import threading
import uuid
import re
from contextlib import nullcontext

from vtn.adapters.llm import LLM, build_generation_plan, normalize_recommendation
from vtn.documents.composer import NoteMarkdownComposer
from vtn.domain.errors import DomainError


def _mermaid_node_label(value):
    value = value.strip().strip(";")
    match = re.search(r"[\[\{\(\"]([^\]\}\)\"]+)[\]\}\)\"]", value)
    if match:
        return match.group(1).strip()
    return re.sub(r"^[A-Za-z0-9_-]+$", "", value).strip()


def normalize_generated_markdown(markdown, title):
    """Remove model preambles and prevent raw Mermaid source from reaching users."""
    markdown = (markdown or "").strip()
    heading = re.search(r"(?m)^#\s+.+$", markdown)
    if heading:
        markdown = markdown[heading.start():]
    else:
        markdown = f"# {title}\n\n{markdown}"

    def mermaid_fallback(match):
        relations = []
        for line in match.group(1).splitlines():
            if "-->" not in line:
                continue
            parts = line.split("-->")
            labels = [_mermaid_node_label(part) for part in parts]
            labels = [label for label in labels if label]
            if len(labels) >= 2:
                relations.append(f"- {' → '.join(labels)}")
        if not relations:
            relations = ["- 核心概念 → 成因理解 → 关系觉察 → 行动练习"]
        return (
            "> 关系图已转换为结构化文字，避免不稳定图表影响阅读。\n\n"
            + "\n".join(relations)
        )

    markdown = re.sub(
        r"```\s*mermaid\s*\n(.*?)```", mermaid_fallback, markdown,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return markdown.strip() + "\n"


def validate_outline(outline, document_title):
    if not isinstance(outline, list) or not outline:
        raise DomainError("NOTE_STRUCTURE_INVALID", "大纲至少需要一个正文篇章")
    normalized = []
    for position, chapter in enumerate(outline, 1):
        if not isinstance(chapter, dict):
            raise DomainError("NOTE_STRUCTURE_INVALID", "大纲篇章格式无效")
        title = str(chapter.get("title") or "").strip()
        if not title:
            raise DomainError("NOTE_STRUCTURE_INVALID", "大纲篇章标题不能为空")
        raw_subtopics = chapter.get("subtopics") or []
        if not isinstance(raw_subtopics, list):
            raise DomainError("NOTE_STRUCTURE_INVALID", "大纲二级主题格式无效")
        subtopics = []
        for raw_subtopic in raw_subtopics:
            subtopic = str(raw_subtopic or "").strip()
            if subtopic and subtopic not in subtopics:
                subtopics.append(subtopic)
        normalized.append({
            "id": str(chapter.get("id") or f"chapter-{position:02d}"),
            "title": title,
            "goal": str(chapter.get("goal") or "根据逐字稿完整展开本章").strip(),
            "subtopics": subtopics,
        })
    if len({chapter["id"] for chapter in normalized}) != len(normalized):
        raise DomainError("NOTE_STRUCTURE_INVALID", "大纲篇章编号不能重复")
    NoteMarkdownComposer(document_title, [chapter["title"] for chapter in normalized], [])
    return normalized


class NoteWorkflow:
    def __init__(
        self, repository, llm, *, run_in_background=True, access_manager=None,
        heavy_task_lock=None,
    ):
        self.repository = repository
        self.llm = llm
        self.run_in_background = run_in_background
        self.access_manager = access_manager
        self.heavy_task_lock = heavy_task_lock
        self._abandoned_task_ids = set()
        self._abandon_lock = threading.Lock()

    def abandon(self, task_id):
        task = self.get_task(task_id)
        if not task:
            raise DomainError("NOTE_TASK_NOT_FOUND", "笔记任务不存在")
        if task["state"] == "complete" or task.get("note_id"):
            raise DomainError("NOTE_ALREADY_COMPLETE", "成品笔记不能通过放弃任务删除")
        active_states = {
            "analyzing", "outline_regenerating", "generating_direct",
            "generating_chapters",
        }
        if task["state"] in active_states:
            with self._abandon_lock:
                self._abandoned_task_ids.add(task_id)
        self._release_usage(task_id)
        if not self.repository.delete_note_task(task_id):
            raise DomainError("NOTE_TASK_NOT_FOUND", "笔记任务不存在")
        return True

    def _finish_if_abandoned(self, task_id):
        with self._abandon_lock:
            if task_id not in self._abandoned_task_ids:
                return False
            self._abandoned_task_ids.discard(task_id)
            return True

    def _heavy_task(self):
        return self.heavy_task_lock or nullcontext()

    def _llm_for_task(self, task):
        bind = getattr(self.llm, "for_profile", None)
        return bind(task.get("llm_profile_id")) if bind else self.llm

    def generation_routes(self):
        describe = getattr(self.llm, "generation_routes", None)
        if describe:
            return describe()
        return {
            "enabled": True,
            "routes": {
                "free": {
                    "id": "free", "label": "免费线路", "available": True,
                    "enabled": True, "description": "不消耗高速次数；速度可能较慢。",
                },
                "paid": {
                    "id": "paid", "label": "高速体验线路", "available": True,
                    "enabled": True,
                    "description": "每次开始会消耗一次高速体验额度。",
                },
            },
        }

    def _profile_for_route(self, route):
        select = getattr(self.llm, "profile_id_for_channel", None)
        if select:
            return select(route)
        active = getattr(self.llm, "active_profile_id", None)
        return active() if active else None

    @staticmethod
    def _uses_high_speed_quota(route):
        return route != "free"

    def _reserve_usage(self, task_id, access_id=None, generation_route=None):
        if self.access_manager is None:
            return
        task = self.get_task(task_id) if access_id is None or generation_route is None else None
        route = generation_route or (task or {}).get("generation_route", "paid")
        if not self._uses_high_speed_quota(route):
            return
        owner = access_id or (task or {}).get("quota_access_id")
        if not owner:
            raise DomainError(
                "ACCESS_REQUIRED",
                "高速笔记线路目前仅对内测用户开放，请输入内测码后继续。",
                retryable=False,
            )
        self.access_manager.consume(owner, "note_generation", task_id, 1)

    def _release_usage(self, task_id):
        if self.access_manager is None:
            return
        task = self.repository.get_note_task(task_id)
        if (
            task
            and task.get("quota_access_id")
            and self._uses_high_speed_quota(task.get("generation_route", "paid"))
        ):
            self.access_manager.release(
                task["quota_access_id"], "note_generation", task_id
            )

    def start_analysis(self, note_input, *, task_id=None, quota_access_id=None):
        source = note_input.get("source")
        if not isinstance(source, dict) or source.get("type") not in {
            "parser", "paste", "file", "note",
        }:
            raise DomainError("INVALID_NOTE_SOURCE", "请选择有效的逐字稿来源")
        source_type = source["type"]
        if source_type in {"paste", "file"}:
            raw_transcript = source.get("transcript")
            if not isinstance(raw_transcript, str):
                raise DomainError("EMPTY_TRANSCRIPT", "逐字稿不能为空")
            if "\x00" in raw_transcript:
                raise DomainError("INVALID_TRANSCRIPT", "逐字稿必须是 UTF-8 文本")
            if len(raw_transcript.encode("utf-8")) > 5 * 1024 * 1024:
                raise DomainError("TRANSCRIPT_TOO_LARGE", "逐字稿不能超过 5 MB")
        transcript = (source.get("transcript") or "").strip()
        source_name = source.get("name", "")
        snapshot = {"type": source_type, "name": source.get("name", "")}
        if source_type == "parser":
            record = self.repository.get_parser_record(source.get("parser_record_id", ""))
            if not record:
                raise DomainError("PARSER_RECORD_NOT_FOUND", "解析记录不存在")
            transcript = record["transcript_text"]
            snapshot = {
                "type": "parser", "parser_record_id": record["id"],
                "title": record["title"], "creator": record["creator"],
                "platform": record["platform"], "source_url": record["source_url"],
            }
        elif source_type == "note":
            original_note = self.repository.get_note(source.get("note_id", ""))
            if not original_note:
                raise DomainError("NOTE_NOT_FOUND", "原笔记不存在")
            transcript = original_note["basis_transcript"]
            source_name = original_note["title"]
            snapshot = {
                **original_note["source_snapshot"],
                "regenerated_from_note_id": original_note["id"],
                "regenerated_from_note_title": original_note["title"],
            }
        if not transcript:
            raise DomainError("EMPTY_TRANSCRIPT", "逐字稿不能为空")
        generation_route = str(note_input.get("generation_route") or "free").strip()
        if generation_route not in {"free", "paid"}:
            raise DomainError("LLM_CHANNEL_INVALID", "请选择有效的笔记线路。")
        profile_id = self._profile_for_route(generation_route)
        task_id = task_id or str(uuid.uuid4())
        owner = note_input.get("device_id") or "local-browser"
        self._reserve_usage(task_id, quota_access_id, generation_route)
        try:
            self.repository.create_note_task(
                {
                    "id": task_id,
                    "device_id": owner,
                    "quota_access_id": quota_access_id,
                    "state": "analyzing",
                    "source_type": source_type,
                    "source_name": source_name or snapshot.get("title", ""),
                    "source_snapshot": snapshot,
                    "basis_transcript": transcript,
                    "request_text": note_input.get("request_text", ""),
                    "llm_profile_id": profile_id,
                    "generation_route": generation_route,
                }
            )
        except Exception:
            if (
                self.access_manager is not None
                and quota_access_id
                and self._uses_high_speed_quota(generation_route)
            ):
                self.access_manager.release(
                    quota_access_id, "note_generation", task_id
                )
            raise
        if snapshot.get("parser_record_id"):
            self.repository.link_parser_note(snapshot["parser_record_id"], task_id)
        self._event(task_id, "state", {"state": "analyzing"})
        if self.run_in_background:
            threading.Thread(target=self._analyze, args=(task_id,), daemon=True).start()
            return self.get_task(task_id)
        self._analyze(task_id)
        return self.get_task(task_id)

    def _analyze(self, task_id):
        task = self.get_task(task_id)
        if not task or self._finish_if_abandoned(task_id):
            return None
        try:
            self._reserve_usage(task_id)
            with self._heavy_task():
                recommendation = normalize_recommendation(
                    self._llm_for_task(task).analyze(
                        task["basis_transcript"], task["request_text"]
                    )
                )
            if self._finish_if_abandoned(task_id):
                return None
            self.repository.update_note_task(
                task_id, state="recommendation_ready",
                proposed_title=recommendation["title"], recommendation=recommendation,
                recommendation_revision=task["transcript_revision"],
                error_code=None, error_message=None,
            )
            self._event(
                task_id, "complete",
                {"state": "recommendation_ready", "title": recommendation["title"]},
            )
        except DomainError as exc:
            if self._finish_if_abandoned(task_id):
                return None
            self._release_usage(task_id)
            self.repository.update_note_task(
                task_id, state="analysis_failed", error_code=exc.code, error_message=exc.message
            )
            self._event(task_id, "error", {"state": "analysis_failed", "code": exc.code,
                                           "message": exc.message, "retryable": exc.retryable})
        except Exception as exc:
            if self._finish_if_abandoned(task_id):
                return None
            self._release_usage(task_id)
            message = f"AI 预读异常：{exc}"
            self.repository.update_note_task(
                task_id, state="analysis_failed", error_code="ANALYSIS_FAILED",
                error_message=message,
            )
            self._event(task_id, "error", {"state": "analysis_failed",
                                           "code": "ANALYSIS_FAILED",
                                           "message": message, "retryable": True})

    def command(self, task_id, command):
        task = self.get_task(task_id)
        if not task:
            raise DomainError("NOTE_TASK_NOT_FOUND", "笔记任务不存在")
        kind = command.get("type")
        if kind == "update_transcript":
            transcript = (command.get("transcript") or "").strip()
            if not transcript:
                raise DomainError("EMPTY_TRANSCRIPT", "逐字稿不能为空")
            return self.repository.update_note_task(
                task_id, basis_transcript=transcript,
                transcript_revision=task["transcript_revision"] + 1,
                state="recommendation_stale",
            )
        if kind == "update_title":
            return self.repository.update_note_task(
                task_id, proposed_title=(command.get("title") or "").strip()
            )
        if kind == "save_settings":
            if task["state"] not in {"recommendation_ready", "outline_ready"}:
                raise DomainError("RECOMMENDATION_NOT_READY", "请先重新分析逐字稿")
            try:
                plan = build_generation_plan(
                    task.get("recommendation"), command.get("settings") or {}
                )
            except ValueError as exc:
                raise DomainError("INVALID_SETTINGS", str(exc)) from exc
            changes = {"final_settings": plan}
            if task["state"] == "outline_ready":
                changes.update(
                    state="recommendation_ready", outline=None, outline_feedback=None,
                    error_code=None, error_message=None,
                )
            return self.repository.update_note_task(task_id, **changes)
        if kind == "start_generation":
            if task["recommendation_revision"] != task["transcript_revision"]:
                raise DomainError("RECOMMENDATION_STALE", "逐字稿已修改，请重新分析")
            if self.run_in_background:
                recommendation = task.get("recommendation") or {}
                recommended_method = (recommendation.get("method") or {}).get(
                    "recommended_id", "direct"
                )
                method = (task.get("final_settings") or {}).get(
                    "method", recommended_method
                )
                starting_state = (
                    "outline_regenerating" if method == "outline" else "generating_direct"
                )
                self.repository.update_note_task(task_id, state=starting_state)
                threading.Thread(target=self._start_generation, args=(task_id,), daemon=True).start()
                return self.get_task(task_id)
            return self._start_generation(task_id)
        if kind == "regenerate_outline":
            if self.run_in_background:
                threading.Thread(
                    target=self._regenerate_outline,
                    args=(task_id, command.get("feedback", "")), daemon=True,
                ).start()
                return self.get_task(task_id)
            return self._regenerate_outline(task_id, command.get("feedback", ""))
        if kind == "confirm_outline":
            if self.run_in_background:
                if task["state"] != "outline_ready":
                    raise DomainError("OUTLINE_NOT_READY", "请先生成大纲")
                self.repository.replace_note_chapters(task_id, task["outline"])
                total = len(task["outline"])
                self.repository.update_note_task(
                    task_id,
                    state="generating_chapters",
                    progress={
                        "stage": "chapters", "completed": 0,
                        "total": total, "current_position": 1 if total else None,
                    },
                )
                self._event(
                    task_id, "state",
                    {"state": "generating_chapters", "completed": 0, "total": total},
                )
                threading.Thread(
                    target=self._generate_chapters, args=(task_id,), daemon=True
                ).start()
                return self.get_task(task_id)
            return self._confirm_outline(task_id)
        if kind == "retry_failed_chapter":
            if self.run_in_background:
                chapters = self.repository.list_note_chapters(task_id)
                next_chapter = next(
                    (chapter for chapter in chapters if chapter["status"] != "complete"), None
                )
                completed = sum(chapter["status"] == "complete" for chapter in chapters)
                self.repository.update_note_task(
                    task_id,
                    state="generating_chapters",
                    progress={
                        "stage": "chapters",
                        "completed": completed,
                        "total": len(chapters),
                        "current_position": next_chapter["position"] if next_chapter else None,
                    },
                    error_code=None,
                    error_message=None,
                )
                self._event(
                    task_id,
                    "state",
                    {
                        "state": "generating_chapters",
                        "completed": completed,
                        "total": len(chapters),
                        "current_position": (
                            next_chapter["position"] if next_chapter else None
                        ),
                    },
                )
                threading.Thread(target=self._generate_chapters, args=(task_id,), daemon=True).start()
                return self.get_task(task_id)
            return self._generate_chapters(task_id)
        if kind == "retry_analysis":
            self.repository.update_note_task(task_id, state="analyzing")
            self._analyze(task_id)
            return self.get_task(task_id)
        if kind == "restart_generation":
            return self._start_generation(task_id, restart=True)
        raise DomainError("INVALID_NOTE_COMMAND", "当前状态不能执行此操作")

    def _start_generation(self, task_id, restart=False):
        if self._finish_if_abandoned(task_id) or not self.get_task(task_id):
            return None
        try:
            self._reserve_usage(task_id)
            task = self.get_task(task_id)
            if task["recommendation_revision"] != task["transcript_revision"]:
                raise DomainError("RECOMMENDATION_STALE", "逐字稿已修改，请重新分析")
            settings = task.get("final_settings") or build_generation_plan(
                task.get("recommendation")
            )
            self.repository.update_note_task(task_id, final_settings=settings)
            task = self.get_task(task_id)
            if settings["method"] == "outline":
                with self._heavy_task():
                    outline = validate_outline(
                        self._llm_for_task(task).generate_outline(task),
                        task["proposed_title"],
                    )
                if self._finish_if_abandoned(task_id):
                    return None
                self.repository.update_note_task(task_id, state="outline_ready", outline=outline)
                self._event(task_id, "state", {"state": "outline_ready"})
                return self.get_task(task_id)
            if (
                len(task.get("basis_transcript") or "") > 15000
                and self._supports_connected_batches()
            ):
                with self._heavy_task():
                    outline = validate_outline(
                        self._llm_for_task(task).generate_outline(task),
                        task["proposed_title"],
                    )
                if self._finish_if_abandoned(task_id):
                    return None
                self.repository.update_note_task(
                    task_id,
                    state="generating_chapters",
                    outline=outline,
                    progress={
                        "stage": "chapters",
                        "completed": 0,
                        "total": len(outline),
                        "current_position": 1,
                    },
                )
                self.repository.replace_note_chapters(task_id, outline)
                self._event(
                    task_id,
                    "state",
                    {
                        "state": "generating_chapters",
                        "completed": 0,
                        "total": len(outline),
                    },
                )
                return self._generate_chapters(task_id)
            self.repository.update_note_task(task_id, state="generating_direct")
            for stage, label in [
                ("understand", "理解逐字稿"), ("organize", "组织结构"),
                ("generate_content", "生成内容"), ("check", "检查遗漏"),
            ]:
                self.repository.update_note_task(task_id, progress={"stage": stage, "label": label})
                self._event(task_id, "progress", {"state": "generating_direct",
                                                  "stage": stage, "label": label})
            with self._heavy_task():
                current_task = self.get_task(task_id)
                direct = self._llm_for_task(current_task).generate_direct(current_task)
            if self._finish_if_abandoned(task_id):
                return None
            chapters = direct.get("chapters") if isinstance(direct, dict) else []
            chapter_titles = [
                str(chapter.get("title") or "").strip()
                for chapter in chapters if isinstance(chapter, dict)
            ]
            module_ids = [module.get("id") for module in settings.get("modules", [])]
            composer = NoteMarkdownComposer(task["proposed_title"], chapter_titles, module_ids)
            chapter_drafts = [
                {
                    "title": str(chapter.get("title") or "").strip(),
                    "content": str(chapter.get("content_markdown") or ""),
                }
                for chapter in chapters if isinstance(chapter, dict)
            ]
            markdown = composer.compose(
                chapter_drafts, direct.get("supplements") or {}, require_supplements=True
            )
            return self._complete(task_id, markdown)
        except DomainError as exc:
            if self._finish_if_abandoned(task_id):
                return None
            self._release_usage(task_id)
            self.repository.update_note_task(
                task_id, state="generation_failed", error_code=exc.code, error_message=exc.message
            )
            self._event(task_id, "error", {"state": "generation_failed", "code": exc.code,
                                           "message": exc.message})
            return self.get_task(task_id)
        except Exception as exc:
            if self._finish_if_abandoned(task_id):
                return None
            self._release_usage(task_id)
            message = f"生成过程异常：{exc}"
            self.repository.update_note_task(
                task_id, state="generation_failed", error_code="GENERATION_FAILED",
                error_message=message,
            )
            self._event(task_id, "error", {"state": "generation_failed",
                                            "code": "GENERATION_FAILED", "message": message})
            return self.get_task(task_id)

    def _regenerate_outline(self, task_id, feedback):
        task = self.get_task(task_id)
        if not task or self._finish_if_abandoned(task_id):
            return None
        if task["state"] != "outline_ready":
            raise DomainError("OUTLINE_NOT_READY", "当前没有可重拟的大纲")
        self.repository.update_note_task(
            task_id, state="outline_regenerating", outline_feedback=feedback
        )
        self._event(task_id, "state", {"state": "outline_regenerating", "feedback": feedback})
        try:
            with self._heavy_task():
                outline = validate_outline(
                    self._llm_for_task(self.get_task(task_id)).generate_outline(
                        self.get_task(task_id), feedback
                    ),
                    task["proposed_title"],
                )
            if self._finish_if_abandoned(task_id):
                return None
        except DomainError as exc:
            if self._finish_if_abandoned(task_id):
                return None
            self._release_usage(task_id)
            self.repository.update_note_task(
                task_id, state="generation_failed", error_code=exc.code,
                error_message=exc.message,
            )
            self._event(
                task_id, "error",
                {"state": "generation_failed", "code": exc.code, "message": exc.message},
            )
            return self.get_task(task_id)
        return self.repository.update_note_task(task_id, state="outline_ready", outline=outline)

    def _confirm_outline(self, task_id):
        task = self.get_task(task_id)
        if task["state"] != "outline_ready":
            raise DomainError("OUTLINE_NOT_READY", "请先生成大纲")
        self.repository.replace_note_chapters(task_id, task["outline"])
        return self._generate_chapters(task_id)

    def _generate_chapters(self, task_id):
        if self._finish_if_abandoned(task_id) or not self.get_task(task_id):
            return None
        self._reserve_usage(task_id)
        self.repository.update_note_task(task_id, state="generating_chapters")
        task = self.get_task(task_id)
        chapters = self.repository.list_note_chapters(task_id)
        module_ids = [
            module.get("id") for module in (task.get("final_settings") or {}).get("modules", [])
        ]
        composer = NoteMarkdownComposer(
            task["proposed_title"], [chapter["title"] for chapter in chapters], module_ids
        )
        if self._supports_connected_batches():
            failed = self._generate_connected_batches(task_id, task, chapters, composer)
            if failed:
                return failed
            chapters = self.repository.list_note_chapters(task_id)

        completed_context = []
        for chapter in chapters:
            if chapter["status"] == "complete":
                completed_context.append(
                    f"《{chapter['title']}》：{chapter['context_summary']}"
                )
                continue
            self.repository.update_note_chapter(
                chapter["id"], status="running", attempt_count=chapter["attempt_count"] + 1
            )
            self._event(task_id, "progress", {"state": "generating_chapters",
                                              "chapter_id": chapter["id"],
                                              "position": chapter["position"]})
            try:
                with self._heavy_task():
                    result = self._llm_for_task(task).generate_chapter(
                        task, chapter, "\n".join(completed_context)
                    )
                if self._finish_if_abandoned(task_id):
                    return None
                result["content"] = composer.normalize_chapter(
                    chapter["title"], result.get("content", "")
                )
            except DomainError as exc:
                if self._finish_if_abandoned(task_id):
                    return None
                self._release_usage(task_id)
                self.repository.update_note_chapter(chapter["id"], status="failed")
                self.repository.update_note_task(
                    task_id, state="chapter_failed", error_code=exc.code,
                    error_message=exc.message,
                )
                self._event(task_id, "error", {"state": "chapter_failed",
                                               "chapter_id": chapter["id"],
                                               "code": exc.code, "message": exc.message})
                return self.get_task(task_id)
            summary = (result.get("summary") or "").strip()
            if not summary:
                summary = re.sub(r"[#>*_`\[\]]", " ", result["content"])
                summary = re.sub(r"\s+", " ", summary).strip()[:300]
            self.repository.update_note_chapter(
                chapter["id"], status="complete", content_md=result["content"],
                context_summary=summary,
            )
            completed_context.append(f"《{chapter['title']}》：{summary}")
        completed_chapters = self.repository.list_note_chapters(task_id)
        chapter_drafts = [
            {"title": chapter["title"], "content": chapter["content_md"]}
            for chapter in completed_chapters
        ]
        try:
            body_markdown = composer.compose(chapter_drafts)
            with self._heavy_task():
                supplements = self._llm_for_task(task).generate_supplements(
                    task, body_markdown
                )
            if self._finish_if_abandoned(task_id):
                return None
            markdown = composer.compose(chapter_drafts, supplements, require_supplements=True)
        except DomainError as exc:
            if self._finish_if_abandoned(task_id):
                return None
            self._release_usage(task_id)
            self.repository.update_note_task(
                task_id, state="generation_failed", error_code=exc.code,
                error_message=exc.message,
            )
            self._event(task_id, "error", {"state": "generation_failed", "code": exc.code,
                                           "message": exc.message})
            return self.get_task(task_id)
        return self._complete(task_id, markdown)

    def _supports_connected_batches(self):
        implementation = getattr(type(self.llm), "generate_chapter_batch", None)
        return implementation is not None and implementation is not LLM.generate_chapter_batch

    @staticmethod
    def _batch_size(task, remaining):
        if len(task.get("basis_transcript") or "") <= 15000:
            return remaining
        detail_id = ((task.get("final_settings") or {}).get("detail") or {}).get(
            "id", "complete"
        )
        return min(remaining, 3 if detail_id == "complete" else 4)

    @staticmethod
    def _completed_chapter_context(chapters):
        blocks = []
        for chapter in chapters:
            if chapter["status"] != "complete":
                continue
            blocks.append(
                f"## {chapter['title']}\n"
                f"本章事实摘要：{chapter['context_summary']}\n"
                f"本章已完成正文：\n{chapter['content_md']}"
            )
        return "\n\n".join(blocks)

    @staticmethod
    def _chapter_with_outline(task, chapter):
        outline = task.get("outline") or []
        plan = outline[chapter["position"] - 1] if chapter["position"] <= len(outline) else {}
        return {
            **chapter,
            "outline_id": str(plan.get("id") or f"chapter-{chapter['position']:02d}"),
            "goal": str(plan.get("goal") or "根据逐字稿完整展开本章"),
            "subtopics": list(plan.get("subtopics") or []),
        }

    def _generate_connected_batches(self, task_id, task, chapters, composer):
        while True:
            if self._finish_if_abandoned(task_id):
                return True
            chapters = self.repository.list_note_chapters(task_id)
            pending = [chapter for chapter in chapters if chapter["status"] != "complete"]
            if not pending:
                return None
            batch_size = self._batch_size(task, len(pending))
            batch = [
                self._chapter_with_outline(task, chapter)
                for chapter in pending[:batch_size]
            ]
            for chapter in batch:
                self.repository.update_note_chapter(
                    chapter["id"],
                    status="running",
                    attempt_count=chapter["attempt_count"] + 1,
                )
                self._event(
                    task_id,
                    "progress",
                    {
                        "state": "generating_chapters",
                        "chapter_id": chapter["id"],
                        "position": chapter["position"],
                    },
                )
            try:
                with self._heavy_task():
                    results = self._llm_for_task(task).generate_chapter_batch(
                        task, batch, self._completed_chapter_context(chapters)
                    )
                if self._finish_if_abandoned(task_id):
                    return True
                expected_ids = [chapter["outline_id"] for chapter in batch]
                result_ids = [result.get("id") for result in results]
                if result_ids != expected_ids:
                    raise DomainError(
                        "LLM_INVALID_RESPONSE",
                        "AI 返回的连续章节与已确认大纲不一致",
                        retryable=True,
                    )
                normalized = []
                for chapter, result in zip(batch, results):
                    content = composer.normalize_chapter(
                        chapter["title"], result.get("content", "")
                    )
                    summary = (result.get("summary") or "").strip()
                    if not summary:
                        summary = re.sub(r"[#>*_`\[\]]", " ", content)
                        summary = re.sub(r"\s+", " ", summary).strip()[:300]
                    normalized.append((chapter, content, summary))
            except DomainError as exc:
                if self._finish_if_abandoned(task_id):
                    return True
                self._release_usage(task_id)
                failed_chapter = batch[0]
                for chapter in batch:
                    self.repository.update_note_chapter(
                        chapter["id"],
                        status="failed" if chapter is failed_chapter else "waiting",
                    )
                self.repository.update_note_task(
                    task_id,
                    state="chapter_failed",
                    error_code=exc.code,
                    error_message=exc.message,
                )
                self._event(
                    task_id,
                    "error",
                    {
                        "state": "chapter_failed",
                        "chapter_id": failed_chapter["id"],
                        "code": exc.code,
                        "message": exc.message,
                    },
                )
                return self.get_task(task_id)
            for chapter, content, summary in normalized:
                self.repository.update_note_chapter(
                    chapter["id"],
                    status="complete",
                    content_md=content,
                    context_summary=summary,
                )

    def _complete(self, task_id, markdown):
        task = self.get_task(task_id)
        if not task or self._finish_if_abandoned(task_id):
            return None
        with self._heavy_task():
            integrity = self._llm_for_task(task).check_integrity(task, markdown)
        if self._finish_if_abandoned(task_id):
            return None
        if integrity.get("check_failed") and integrity.get("status") == "ok":
            integrity = {**integrity, "status": "check_unavailable"}
        note_id = task.get("note_id") or str(uuid.uuid4())
        if not task.get("note_id"):
            self.repository.create_note(
                {
                    "id": note_id, "task_id": task_id, "title": task["proposed_title"],
                    "current_markdown": markdown, "integrity": integrity,
                    "source_snapshot": task["source_snapshot"],
                    "basis_transcript": task["basis_transcript"],
                }
            )
        self.repository.update_note_task(task_id, state="complete", note_id=note_id,
                                         progress={"stage": "complete", "label": "完成"})
        self._event(task_id, "complete", {"state": "complete", "note_id": note_id})
        return self.get_task(task_id)

    def get_task(self, task_id):
        task = self.repository.get_note_task(task_id)
        if not task or not task.get("recommendation"):
            return task
        normalized = normalize_recommendation(task["recommendation"])
        if normalized != task["recommendation"]:
            return self.repository.update_note_task(task_id, recommendation=normalized)
        return task

    def subscribe(self, task_id, after_seq=0):
        return self.repository.list_events("note", task_id, after_seq)

    def _event(self, task_id, event_type, payload):
        if not self.repository.get_note_task(task_id):
            return None
        return self.repository.append_event("note", task_id, event_type, payload)
