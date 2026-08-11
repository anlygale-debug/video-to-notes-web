import base64
import json
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from vtn.domain.errors import DomainError


def _simplify_chinese_transcript(text, detected_language=None):
    language = str(detected_language or "").strip().lower()
    if language and not language.startswith("zh"):
        return text
    if not language and not any("\u3400" <= character <= "\u9fff" for character in text):
        return text
    try:
        from zhconv import convert
    except ImportError as exc:
        raise DomainError(
            "TRANSCRIPT_SIMPLIFIER_UNAVAILABLE",
            "缺少简体中文转换依赖 zhconv，请安装后重试。",
            retryable=False,
        ) from exc
    return convert(text, "zh-cn")


class Transcriber:
    def transcribe(self, audio_path) -> str:
        raise NotImplementedError


class WhisperTranscriber(Transcriber):
    _model = None

    def __init__(self, model_name="tiny"):
        self.model_name = model_name

    def transcribe(self, audio_path):
        try:
            import whisper
            if WhisperTranscriber._model is None:
                WhisperTranscriber._model = whisper.load_model(self.model_name)
            result = WhisperTranscriber._model.transcribe(
                str(audio_path), task="transcribe", fp16=False
            )
            text = (result.get("text") or "").strip()
            text = _simplify_chinese_transcript(text, result.get("language"))
            if not text:
                raise ValueError("empty transcript")
            return text
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError("TRANSCRIPTION_FAILED", f"语音转录失败：{exc}", retryable=True)


class FasterWhisperTranscriber(Transcriber):
    _models = {}

    def __init__(self, model_name="tiny"):
        self.model_name = model_name

    def transcribe(self, audio_path):
        try:
            from faster_whisper import WhisperModel

            if self.model_name not in FasterWhisperTranscriber._models:
                FasterWhisperTranscriber._models[self.model_name] = WhisperModel(
                    self.model_name,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=2,
                )
            segments, info = FasterWhisperTranscriber._models[
                self.model_name
            ].transcribe(
                str(audio_path),
                task="transcribe",
                beam_size=1,
                vad_filter=True,
                condition_on_previous_text=True,
            )
            text = "".join((segment.text or "") for segment in segments).strip()
            text = _simplify_chinese_transcript(text, info.language)
            if not text:
                raise ValueError("empty transcript")
            return text
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError(
                "TRANSCRIPTION_FAILED",
                f"本地语音转录失败：{exc}",
                retryable=True,
            ) from exc


class CloudflareTranscriber(Transcriber):
    MODEL = "@cf/openai/whisper-large-v3-turbo"

    def __init__(
        self,
        account_id,
        api_token,
        *,
        timeout_seconds=45,
        initial_prompt="",
        max_upload_bytes=2 * 1024 * 1024,
        segment_seconds=180,
        max_attempts=3,
        retry_backoff_seconds=1,
        bypass_proxy=False,
        direct_fallback=False,
        direct_timeout_seconds=15,
    ):
        self.account_id = account_id
        self.api_token = api_token
        self.timeout_seconds = timeout_seconds
        self.initial_prompt = initial_prompt
        self.max_upload_bytes = max_upload_bytes
        self.segment_seconds = segment_seconds
        self.max_attempts = max(1, int(max_attempts))
        self.retry_backoff_seconds = max(0, float(retry_backoff_seconds))
        self.bypass_proxy = bool(bypass_proxy)
        self.direct_fallback = bool(direct_fallback)
        self.direct_timeout_seconds = max(1, float(direct_timeout_seconds))

    @staticmethod
    def _ssl_context():
        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            return ssl.create_default_context()

    def transcribe(self, audio_path):
        audio_path = Path(audio_path)
        if audio_path.stat().st_size <= self.max_upload_bytes:
            return self._transcribe_bytes(audio_path.read_bytes())
        try:
            with tempfile.TemporaryDirectory(prefix="vtn-cloudflare-audio-") as tempdir:
                output_pattern = str(Path(tempdir) / "segment-%05d.mp3")
                subprocess.run(
                    [
                        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-i", str(audio_path), "-vn", "-ac", "1", "-ar", "16000",
                        "-b:a", "64k", "-f", "segment", "-segment_time",
                        str(self.segment_seconds), "-reset_timestamps", "1", output_pattern,
                    ],
                    check=True,
                    capture_output=True,
                    timeout=max(self.timeout_seconds, 300),
                )
                parts = sorted(Path(tempdir).glob("segment-*.mp3"))
                if not parts:
                    raise ValueError("ffmpeg did not create audio segments")
                return "\n".join(
                    self._transcribe_bytes(part.read_bytes()) for part in parts
                ).strip()
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError(
                "TRANSCRIPTION_FAILED",
                f"云端转录前的音频分段失败：{exc}",
                retryable=True,
            ) from exc

    def _transcribe_bytes(self, audio_bytes):
        use_direct_connection = self.bypass_proxy
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self._transcribe_bytes_once(
                    audio_bytes,
                    bypass_proxy=use_direct_connection,
                )
            except DomainError as exc:
                if not exc.retryable or attempt >= self.max_attempts:
                    raise
                if self.bypass_proxy:
                    use_direct_connection = True
                elif (
                    self.direct_fallback
                    and exc.code == "TRANSCRIPTION_UPLOAD_INTERRUPTED"
                ):
                    use_direct_connection = not use_direct_connection
                else:
                    use_direct_connection = False
                time.sleep(self.retry_backoff_seconds * (2 ** (attempt - 1)))

    def _transcribe_bytes_once(self, audio_bytes, *, bypass_proxy=False):
        payload = {
            "audio": base64.b64encode(audio_bytes).decode("ascii"),
            "task": "transcribe",
            "vad_filter": True,
            "beam_size": 5,
            "condition_on_previous_text": True,
        }
        if self.initial_prompt:
            payload["initial_prompt"] = self.initial_prompt
        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{self.account_id}/ai/run/{self.MODEL}"
        )
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            if bypass_proxy:
                opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({}),
                    urllib.request.HTTPSHandler(context=self._ssl_context()),
                )
                response_context = opener.open(
                    request,
                    timeout=min(self.timeout_seconds, self.direct_timeout_seconds),
                )
            else:
                response_context = urllib.request.urlopen(
                    request,
                    timeout=self.timeout_seconds,
                    context=self._ssl_context(),
                )
            with response_context as response:
                result = json.loads(response.read())
            transcription = result.get("result", {})
            text = (transcription.get("text") or "").strip()
            info = transcription.get("transcription_info") or {}
            detected_language = transcription.get("language") or info.get("language")
            text = _simplify_chinese_transcript(text, detected_language)
            if not result.get("success") or not text:
                raise ValueError("empty transcript")
            return text
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise DomainError(
                    "TRANSCRIPTION_AUTH_FAILED",
                    "Cloudflare 转录凭证无效或没有 Workers AI 权限。",
                    retryable=False,
                ) from exc
            raise DomainError(
                "TRANSCRIPTION_FAILED",
                f"Cloudflare 转录请求失败（HTTP {exc.code}）。",
                retryable=exc.code == 429 or exc.code >= 500,
            ) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise DomainError(
                    "TRANSCRIPTION_UPLOAD_TIMEOUT",
                    "Cloudflare 音频上传超时，已停止本次解析，请检查网络后重试。",
                    retryable=True,
                ) from exc
            if isinstance(exc.reason, BrokenPipeError):
                raise DomainError(
                    "TRANSCRIPTION_UPLOAD_INTERRUPTED",
                    "Cloudflare 音频上传连接中断，已停止本次解析，请检查网络后重试。",
                    retryable=True,
                ) from exc
            if isinstance(exc.reason, (ConnectionError, ssl.SSLError)):
                raise DomainError(
                    "TRANSCRIPTION_UPLOAD_INTERRUPTED",
                    "Cloudflare 音频上传连接中断，系统自动重试后仍未恢复，请稍后再试。",
                    retryable=True,
                ) from exc
            raise DomainError(
                "TRANSCRIPTION_FAILED",
                f"Cloudflare 转录连接失败：{exc.reason}",
                retryable=True,
            ) from exc
        except TimeoutError as exc:
            raise DomainError(
                "TRANSCRIPTION_UPLOAD_TIMEOUT",
                "Cloudflare 音频上传超时，已停止本次解析，请检查网络后重试。",
                retryable=True,
            ) from exc
        except BrokenPipeError as exc:
            raise DomainError(
                "TRANSCRIPTION_UPLOAD_INTERRUPTED",
                "Cloudflare 音频上传连接中断，已停止本次解析，请检查网络后重试。",
                retryable=True,
            ) from exc
        except ConnectionError as exc:
            raise DomainError(
                "TRANSCRIPTION_UPLOAD_INTERRUPTED",
                "Cloudflare 音频上传连接中断，系统自动重试后仍未恢复，请稍后再试。",
                retryable=True,
            ) from exc
        except ssl.SSLError as exc:
            raise DomainError(
                "TRANSCRIPTION_UPLOAD_INTERRUPTED",
                "Cloudflare 音频上传连接中断，系统自动重试后仍未恢复，请稍后再试。",
                retryable=True,
            ) from exc
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError("TRANSCRIPTION_FAILED", f"云端语音转录失败：{exc}", retryable=True)


def _probe_audio_duration(audio_path):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return max(0.0, float(result.stdout.strip()))
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0.0


class SwitchableTranscriber(Transcriber):
    def __init__(
        self,
        provider_store,
        local_transcriber,
        *,
        cloudflare_factory=None,
        duration_probe=None,
    ):
        self.provider_store = provider_store
        self.local_transcriber = local_transcriber
        self.cloudflare_factory = cloudflare_factory or (
            lambda account_id, api_token: CloudflareTranscriber(
                account_id,
                api_token,
                max_attempts=3,
                direct_fallback=True,
            )
        )
        self.duration_probe = duration_probe or _probe_audio_duration

    def transcribe(self, audio_path):
        return self.transcribe_with_provider(
            audio_path,
            self.provider_store.status()["active_provider"],
        )

    def available_providers(self):
        status = self.provider_store.status()
        return {
            "local": True,
            "cloudflare": bool(status["cloudflare"]["configured"]),
        }

    def transcribe_with_provider(self, audio_path, provider):
        if provider not in {"local", "cloudflare"}:
            raise DomainError(
                "TRANSCRIPTION_PROVIDER_INVALID",
                "请选择云端高质量转录或本地免费转录。",
                retryable=False,
            )
        if provider == "local":
            return self.local_transcriber.transcribe(audio_path)
        credentials = self.provider_store.cloudflare_credentials()
        if not credentials:
            raise DomainError(
                "TRANSCRIPTION_CONFIG_MISSING",
                "云端高质量转录暂未配置，请改用本地免费转录。",
                retryable=False,
            )
        transcriber = self.cloudflare_factory(*credentials)
        text = transcriber.transcribe(audio_path)
        self.provider_store.record_cloudflare_usage(
            self.duration_probe(audio_path)
        )
        return text


class FakeTranscriber(Transcriber):
    def __init__(self, text="这是一份固定逐字稿，用于本地验收。"):
        self.text = text

    def transcribe(self, audio_path):
        return self.text
