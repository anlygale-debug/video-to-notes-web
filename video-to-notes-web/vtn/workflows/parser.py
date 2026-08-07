import shutil
import tempfile
import threading
import uuid
from contextlib import nullcontext
from pathlib import Path

from vtn.adapters.media import detect_platform
from vtn.domain.errors import DomainError


SAFE_MEDIA_RESOLVE_MESSAGE = (
    "视频解析失败：视频平台暂时拒绝解析，可能需要登录凭证或链接已失效"
)


class ParserWorkflow:
    def __init__(
        self, repository, media, transcriber, *, run_in_background=True,
        access_manager=None, heavy_task_lock=None,
    ):
        self.repository = repository
        self.media = media
        self.transcriber = transcriber
        self.run_in_background = run_in_background
        self.access_manager = access_manager
        self.heavy_task_lock = heavy_task_lock

    def _heavy_task(self):
        return self.heavy_task_lock or nullcontext()

    def start_parse(self, device_id, source_url):
        task_id = str(uuid.uuid4())
        task = self.repository.create_parser_task(
            {
                "id": task_id,
                "device_id": device_id,
                "source_url": source_url,
                "platform_hint": detect_platform(source_url),
                "state": "created",
            }
        )
        self._event(task_id, "state", {"state": "created"})
        if self.run_in_background:
            threading.Thread(target=self._run, args=(task_id,), daemon=True).start()
            return self.get_task(task_id)
        self._run(task_id)
        return self.get_task(task_id)

    def _transition(self, task_id, state, *, stage=None, label=None, percent=None):
        progress = (
            {"stage": stage, "label": label, "percent": percent} if stage else {}
        )
        self.repository.update_parser_task(
            task_id, state=state, progress=progress, error_code=None, error_message=None,
            error_retryable=None,
        )
        self._event(task_id, "state", {"state": state, **progress})

    def _run(self, task_id):
        task = self.get_task(task_id)
        tempdir = Path(tempfile.mkdtemp(prefix="vtn-parser-"))
        try:
            if self.access_manager is not None:
                self.access_manager.ensure_parser_calls_enabled()
            self._transition(
                task_id, "resolving", stage="resolve", label="识别视频来源", percent=10
            )
            meta = self.media.resolve(task["source_url"])
            if self.access_manager is not None:
                duration = int(meta.get("duration_seconds") or 0)
                if duration <= 0:
                    raise DomainError(
                        "VIDEO_DURATION_UNKNOWN",
                        "无法确认视频时长，为避免意外消耗额度，暂不转录这个视频",
                        retryable=False,
                    )
                self.access_manager.consume(
                    task["device_id"], "transcription_seconds", task_id, duration
                )
            self._transition(
                task_id, "downloading", stage="download", label="获取视频音频", percent=30
            )
            with self._heavy_task():
                audio_path = self.media.download_audio(task["source_url"], tempdir)
                self._transition(
                    task_id, "transcribing", stage="transcribe", label="生成逐字稿", percent=55
                )
                transcript = self.transcriber.transcribe(audio_path)
            self._transition(
                task_id, "saving", stage="save", label="整理并保存结果", percent=90
            )
            record_id = str(uuid.uuid4())
            self.repository.create_parser_record(
                {
                    "id": record_id,
                    "access_id": task["device_id"] if self.access_manager is not None else None,
                    **meta,
                    "transcript_text": transcript,
                    "transcript_format_version": 2,
                }
            )
            self.repository.update_parser_task(
                task_id, state="completed", record_id=record_id,
                progress={"stage": "complete", "label": "解析完成", "percent": 100},
            )
            self._event(task_id, "complete", {"state": "completed", "record_id": record_id})
        except DomainError as exc:
            if self.access_manager is not None:
                self.access_manager.release(
                    task["device_id"], "transcription_seconds", task_id
                )
            self.repository.update_parser_task(
                task_id, state="failed", progress={},
                error_code=exc.code, error_message=exc.message,
                error_retryable=exc.retryable,
            )
            self._event(
                task_id, "error",
                {"state": "failed", "code": exc.code, "message": exc.message,
                 "retryable": exc.retryable},
            )
        except Exception as exc:
            if self.access_manager is not None:
                self.access_manager.release(
                    task["device_id"], "transcription_seconds", task_id
                )
            self.repository.update_parser_task(
                task_id, state="failed", progress={}, error_code="PARSER_FAILED",
                error_message=f"解析失败：{exc}", error_retryable=True,
            )
            self._event(
                task_id, "error",
                {"state": "failed", "code": "PARSER_FAILED",
                 "message": f"解析失败：{exc}", "retryable": True},
            )
        finally:
            shutil.rmtree(tempdir, ignore_errors=True)

    def command(self, task_id, command):
        task = self.get_task(task_id)
        if not task:
            raise DomainError("PARSER_TASK_NOT_FOUND", "解析任务不存在")
        if command != "retry" or task["state"] != "failed":
            raise DomainError("INVALID_PARSER_COMMAND", "当前状态不能执行此操作")
        self.repository.update_parser_task(
            task_id, state="retrying", retry_count=task["retry_count"] + 1
        )
        self._event(task_id, "state", {"state": "retrying"})
        if self.run_in_background:
            threading.Thread(target=self._run, args=(task_id,), daemon=True).start()
            return self.get_task(task_id)
        self._run(task_id)
        return self.get_task(task_id)

    def get_task(self, task_id):
        task = self.repository.get_parser_task(task_id)
        if task and task.get("error_code") == "MEDIA_RESOLVE_FAILED":
            return {**task, "error_message": SAFE_MEDIA_RESOLVE_MESSAGE}
        return task

    def subscribe(self, task_id, after_seq=0):
        return self.repository.list_events("parser", task_id, after_seq)

    def _event(self, task_id, event_type, payload):
        return self.repository.append_event("parser", task_id, event_type, payload)
