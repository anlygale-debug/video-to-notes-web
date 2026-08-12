import tempfile
import types
import unittest
import json
import base64
import http.client
import io
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import wave
from pathlib import Path
from unittest.mock import patch

from vtn.adapters.media import FakePlatformMedia, YtDlpPlatformMedia, detect_platform
from vtn.adapters.llm import FakeLLM, OpenAICompatibleLLM
from vtn.adapters.transcription import (
    CloudflareTranscriber,
    FakeTranscriber,
    FasterWhisperTranscriber,
    SwitchableTranscriber,
    WhisperTranscriber,
)
from vtn.domain.errors import DomainError
from vtn.storage.sqlite import SQLiteRepository
from vtn.workflows.parser import ParserWorkflow
from vtn.workflows.notes import NoteWorkflow
from vtn.bootstrap import build_transcriber
from vtn.transcription_provider import TranscriptionProviderStore


class ParserWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = SQLiteRepository(Path(self.tempdir.name) / "test.sqlite3")
        self.repo.migrate()

    def tearDown(self):
        self.repo.close()
        self.tempdir.cleanup()

    def test_whisper_transcriber_returns_simplified_chinese(self):
        calls = {}

        class Model:
            def transcribe(self, audio_path, **options):
                calls["audio_path"] = audio_path
                calls["options"] = options
                return {"text": "學習 AI 後，建立自己的知識庫。"}

        whisper = types.SimpleNamespace(load_model=lambda _name: Model())
        zhconv = types.SimpleNamespace(
            convert=lambda text, locale: "学习 AI 后，建立自己的知识库。"
            if locale == "zh-cn" else text
        )
        WhisperTranscriber._model = None
        with patch.dict("sys.modules", {"whisper": whisper, "zhconv": zhconv}):
            transcript = WhisperTranscriber().transcribe("audio.mp3")

        self.assertEqual(transcript, "学习 AI 后，建立自己的知识库。")
        self.assertNotIn("language", calls["options"])
        self.assertEqual(calls["options"]["task"], "transcribe")

    def test_whisper_transcriber_keeps_english_audio_in_english(self):
        calls = {}
        expected = "Anything that is meant for you will never pass you by."

        class Model:
            def transcribe(self, audio_path, **options):
                calls["options"] = options
                return {"text": expected, "language": "en"}

        whisper = types.SimpleNamespace(load_model=lambda _name: Model())
        WhisperTranscriber._model = None
        with patch.dict("sys.modules", {"whisper": whisper, "zhconv": None}):
            transcript = WhisperTranscriber().transcribe("english-audio.mp3")

        self.assertEqual(transcript, expected)
        self.assertNotIn("language", calls["options"])

    def test_whisper_transcriber_fails_clearly_when_simplifier_is_unavailable(self):
        class Model:
            def transcribe(self, _audio_path, **_options):
                return {"text": "這是一份繁體逐字稿。"}

        whisper = types.SimpleNamespace(load_model=lambda _name: Model())
        WhisperTranscriber._model = None
        with patch.dict("sys.modules", {"whisper": whisper, "zhconv": None}):
            with self.assertRaises(DomainError) as context:
                WhisperTranscriber().transcribe("audio.mp3")

        self.assertEqual(context.exception.code, "TRANSCRIPT_SIMPLIFIER_UNAVAILABLE")
        self.assertFalse(context.exception.retryable)

    def test_faster_whisper_transcriber_returns_joined_simplified_chinese(self):
        class Segment:
            def __init__(self, text, end):
                self.text = text
                self.end = end

        class Model:
            def __init__(self, *_args, **_options):
                pass

            def transcribe(self, _audio_path, **_options):
                return (
                    iter([Segment("這是一份", 25), Segment("本地逐字稿。", 60)]),
                    types.SimpleNamespace(language="zh", duration=60),
                )

        faster_whisper = types.SimpleNamespace(WhisperModel=Model)
        progress = []
        FasterWhisperTranscriber._models.clear()
        with patch.dict("sys.modules", {"faster_whisper": faster_whisper}):
            transcript = FasterWhisperTranscriber().transcribe(
                "audio.m4a",
                progress_callback=lambda processed, total: progress.append(
                    (processed, total)
                ),
            )

        self.assertEqual(transcript, "这是一份本地逐字稿。")
        self.assertEqual(progress, [(0, 60), (25, 60), (60, 60), (60, 60)])

    def test_cloudflare_transcriber_returns_simplified_chinese(self):
        audio_path = Path(self.tempdir.name) / "audio.wav"
        audio_path.write_bytes(b"test audio")
        captured = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(
                    {"success": True, "result": {"text": "這是一份心理學逐字稿。"}}
                ).encode()

        def open_request(request, timeout, context=None):
            captured["request"] = request
            captured["timeout"] = timeout
            captured["context"] = context
            return Response()

        with patch("urllib.request.urlopen", open_request):
            transcript = CloudflareTranscriber(
                account_id="account-id",
                api_token="api-token",
            ).transcribe(audio_path)

        payload = json.loads(captured["request"].data)
        self.assertEqual(transcript, "这是一份心理学逐字稿。")
        self.assertEqual(base64.b64decode(payload["audio"]), b"test audio")
        self.assertNotIn("language", payload)
        self.assertEqual(payload["task"], "transcribe")
        self.assertTrue(payload["vad_filter"])
        self.assertEqual(captured["timeout"], 45)
        self.assertIsNotNone(captured["context"])
        self.assertNotEqual(captured["context"].verify_mode, 0)

    def test_cloudflare_transcriber_keeps_english_audio_in_english(self):
        audio_path = Path(self.tempdir.name) / "english-audio.wav"
        audio_path.write_bytes(b"english test audio")
        captured = {}
        expected = (
            "You are free to let go, because anything that is meant for you "
            "will never pass you by."
        )

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(
                    {
                        "success": True,
                        "result": {
                            "text": expected,
                            "transcription_info": {"language": "en"},
                        },
                    }
                ).encode()

        def open_request(request, timeout, context=None):
            captured["payload"] = json.loads(request.data)
            return Response()

        with patch("urllib.request.urlopen", open_request):
            transcript = CloudflareTranscriber(
                "account-id", "api-token"
            ).transcribe(audio_path)

        self.assertEqual(transcript, expected)
        self.assertNotIn("language", captured["payload"])
        self.assertEqual(captured["payload"]["task"], "transcribe")

    def test_cloudflare_transcriber_reports_invalid_credentials(self):
        audio_path = Path(self.tempdir.name) / "audio.wav"
        audio_path.write_bytes(b"test audio")

        def reject_request(request, timeout, context=None):
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                {},
                io.BytesIO(b'{"success":false}'),
            )

        with patch("urllib.request.urlopen", reject_request):
            with self.assertRaises(DomainError) as context:
                CloudflareTranscriber("account-id", "bad-token").transcribe(audio_path)

        self.assertEqual(context.exception.code, "TRANSCRIPTION_AUTH_FAILED")
        self.assertFalse(context.exception.retryable)

    def test_cloudflare_upload_timeout_stops_with_stable_retryable_error(self):
        audio_path = Path(self.tempdir.name) / "audio.wav"
        audio_path.write_bytes(b"test audio")

        def timeout_request(request, timeout, context=None):
            raise TimeoutError("The write operation timed out")

        with patch("urllib.request.urlopen", timeout_request):
            with self.assertRaises(DomainError) as context:
                CloudflareTranscriber("account-id", "api-token").transcribe(audio_path)

        self.assertEqual(context.exception.code, "TRANSCRIPTION_UPLOAD_TIMEOUT")
        self.assertIn("上传超时", context.exception.message)
        self.assertIn("已停止", context.exception.message)
        self.assertTrue(context.exception.retryable)

    def test_cloudflare_broken_upload_stops_with_stable_retryable_error(self):
        audio_path = Path(self.tempdir.name) / "audio.wav"
        audio_path.write_bytes(b"test audio")

        def broken_request(request, timeout, context=None):
            raise BrokenPipeError("Broken pipe")

        with patch("urllib.request.urlopen", broken_request):
            with self.assertRaises(DomainError) as context:
                CloudflareTranscriber("account-id", "api-token").transcribe(audio_path)

        self.assertEqual(context.exception.code, "TRANSCRIPTION_UPLOAD_INTERRUPTED")
        self.assertIn("连接中断", context.exception.message)
        self.assertIn("已停止", context.exception.message)
        self.assertTrue(context.exception.retryable)

    def test_cloudflare_wrapped_upload_timeout_keeps_stable_error(self):
        audio_path = Path(self.tempdir.name) / "audio.wav"
        audio_path.write_bytes(b"test audio")

        def timeout_request(request, timeout, context=None):
            raise urllib.error.URLError(TimeoutError("write operation timed out"))

        with patch("urllib.request.urlopen", timeout_request):
            with self.assertRaises(DomainError) as context:
                CloudflareTranscriber("account-id", "api-token").transcribe(audio_path)

        self.assertEqual(context.exception.code, "TRANSCRIPTION_UPLOAD_TIMEOUT")
        self.assertTrue(context.exception.retryable)

    def test_cloudflare_transcription_recovers_from_temporary_remote_disconnect(self):
        audio_path = Path(self.tempdir.name) / "audio.wav"
        audio_path.write_bytes(b"test audio")
        attempts = 0

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(
                    {"success": True, "result": {"text": "自动重试后生成的逐字稿。"}}
                ).encode()

        def temporary_disconnect(_request, timeout=None, context=None):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise http.client.RemoteDisconnected(
                    "Remote end closed connection without response"
                )
            return Response()

        with patch("urllib.request.urlopen", temporary_disconnect), patch(
            "vtn.adapters.transcription.time.sleep"
        ):
            transcript = CloudflareTranscriber(
                "account-id", "api-token"
            ).transcribe(audio_path)

        self.assertEqual(transcript, "自动重试后生成的逐字稿。")

    def test_cloudflare_transcription_fails_clearly_after_retries_are_exhausted(self):
        audio_path = Path(self.tempdir.name) / "audio.wav"
        audio_path.write_bytes(b"test audio")
        attempts = 0

        def always_disconnect(_request, timeout=None, context=None):
            nonlocal attempts
            attempts += 1
            raise http.client.RemoteDisconnected(
                "Remote end closed connection without response"
            )

        with patch("urllib.request.urlopen", always_disconnect), patch(
            "vtn.adapters.transcription.time.sleep"
        ), self.assertRaises(DomainError) as context:
            CloudflareTranscriber("account-id", "api-token").transcribe(audio_path)

        self.assertEqual(attempts, 3)
        self.assertEqual(context.exception.code, "TRANSCRIPTION_UPLOAD_INTERRUPTED")
        self.assertIn("连接中断", context.exception.message)
        self.assertNotIn("Remote end closed", context.exception.message)

    def test_cloudflare_ssl_disconnect_fails_clearly_after_retries_are_exhausted(self):
        audio_path = Path(self.tempdir.name) / "audio.wav"
        audio_path.write_bytes(b"test audio")

        def ssl_disconnect(_request, timeout=None, context=None):
            raise ssl.SSLEOFError(
                8,
                "EOF occurred in violation of protocol",
            )

        with patch("urllib.request.urlopen", ssl_disconnect), patch(
            "vtn.adapters.transcription.time.sleep"
        ), self.assertRaises(DomainError) as context:
            CloudflareTranscriber("account-id", "api-token").transcribe(audio_path)

        self.assertEqual(context.exception.code, "TRANSCRIPTION_UPLOAD_INTERRUPTED")
        self.assertIn("连接中断", context.exception.message)
        self.assertNotIn("SSL", context.exception.message)

    def test_cloudflare_wrapped_ssl_disconnect_uses_stable_retryable_error(self):
        audio_path = Path(self.tempdir.name) / "audio.wav"
        audio_path.write_bytes(b"test audio")

        def wrapped_ssl_disconnect(_request, timeout=None, context=None):
            raise urllib.error.URLError(
                ssl.SSLEOFError(8, "EOF occurred in violation of protocol")
            )

        with patch("urllib.request.urlopen", wrapped_ssl_disconnect), patch(
            "vtn.adapters.transcription.time.sleep"
        ), self.assertRaises(DomainError) as context:
            CloudflareTranscriber("account-id", "api-token").transcribe(audio_path)

        self.assertEqual(context.exception.code, "TRANSCRIPTION_UPLOAD_INTERRUPTED")
        self.assertIn("连接中断", context.exception.message)
        self.assertNotIn("SSL", context.exception.message)

    def test_transcriber_configuration_uses_lightweight_local_default_and_allows_cloudflare(self):
        local = build_transcriber({})
        cloud = build_transcriber(
            {
                "VTN_TRANSCRIBER": "cloudflare",
                "CLOUDFLARE_ACCOUNT_ID": "account-id",
                "CLOUDFLARE_API_TOKEN": "api-token",
                "VTN_TRANSCRIPTION_PROMPT": "心理学专有名词",
            }
        )

        self.assertIsInstance(local, FasterWhisperTranscriber)
        self.assertEqual(local.model_name, "tiny")
        self.assertIsInstance(cloud, CloudflareTranscriber)
        self.assertEqual(cloud.initial_prompt, "心理学专有名词")
        self.assertFalse(cloud.bypass_proxy)
        self.assertTrue(cloud.direct_fallback)
        self.assertEqual(cloud.max_attempts, 3)

    def test_configured_cloudflare_transcriber_falls_back_to_direct_connection(self):
        audio_path = Path(self.tempdir.name) / "audio.wav"
        audio_path.write_bytes(b"test audio")
        cloud = build_transcriber(
            {
                "VTN_TRANSCRIBER": "cloudflare",
                "CLOUDFLARE_ACCOUNT_ID": "account-id",
                "CLOUDFLARE_API_TOKEN": "api-token",
            }
        )

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(
                    {"success": True, "result": {"text": "直连生成的逐字稿。"}}
                ).encode()

        class DirectOpener:
            def open(self, _request, timeout=None):
                return Response()

        proxy_attempts = 0

        def proxy_disconnect(_request, timeout=None, context=None):
            nonlocal proxy_attempts
            proxy_attempts += 1
            raise http.client.RemoteDisconnected(
                "Remote end closed connection without response"
            )

        with patch(
            "urllib.request.urlopen",
            side_effect=proxy_disconnect,
        ), patch("urllib.request.build_opener", return_value=DirectOpener()):
            transcript = cloud.transcribe(audio_path)

        self.assertEqual(proxy_attempts, 1)
        self.assertEqual(transcript, "直连生成的逐字稿。")

    def test_configured_cloudflare_transcriber_returns_to_proxy_after_direct_timeout(self):
        audio_path = Path(self.tempdir.name) / "audio.wav"
        audio_path.write_bytes(b"test audio")
        cloud = build_transcriber(
            {
                "VTN_TRANSCRIBER": "cloudflare",
                "CLOUDFLARE_ACCOUNT_ID": "account-id",
                "CLOUDFLARE_API_TOKEN": "api-token",
            }
        )
        proxy_attempts = 0
        direct_attempts = 0

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(
                    {"success": True, "result": {"text": "切回代理后生成的逐字稿。"}}
                ).encode()

        def proxy_recovers(_request, timeout=None, context=None):
            nonlocal proxy_attempts
            proxy_attempts += 1
            if proxy_attempts == 1:
                raise http.client.RemoteDisconnected(
                    "Remote end closed connection without response"
                )
            return Response()

        class TimedOutDirectOpener:
            def open(self, _request, timeout=None):
                nonlocal direct_attempts
                direct_attempts += 1
                raise TimeoutError("direct connection timed out")

        with patch("urllib.request.urlopen", side_effect=proxy_recovers), patch(
            "urllib.request.build_opener",
            return_value=TimedOutDirectOpener(),
        ), patch("vtn.adapters.transcription.time.sleep"):
            transcript = cloud.transcribe(audio_path)

        self.assertEqual(proxy_attempts, 2)
        self.assertEqual(direct_attempts, 1)
        self.assertEqual(transcript, "切回代理后生成的逐字稿。")

    def test_switchable_transcriber_changes_provider_without_restart(self):
        provider_store = TranscriptionProviderStore(
            Path(self.tempdir.name) / "transcription-provider.json"
        )
        provider_store.save_cloudflare("a" * 32, "token-" + ("x" * 32))
        switchable = SwitchableTranscriber(
            provider_store,
            FakeTranscriber("本地结果"),
            cloudflare_factory=lambda _account_id, _api_token: FakeTranscriber(
                "Cloudflare 结果"
            ),
            duration_probe=lambda _path: 600,
        )

        self.assertEqual(switchable.transcribe("audio.mp3"), "本地结果")
        provider_store.activate("cloudflare")
        self.assertEqual(switchable.transcribe("audio.mp3"), "Cloudflare 结果")
        self.assertEqual(
            provider_store.status()["usage"]["today_transcription_minutes"],
            10,
        )

    def test_cloudflare_transcriber_segments_large_audio_before_upload(self):
        audio_path = Path(self.tempdir.name) / "long.wav"
        with wave.open(str(audio_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(8000)
            wav.writeframes(b"\0\0" * 8000 * 3)
        uploads = []
        progress = []

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                index = len(uploads)
                return json.dumps(
                    {"success": True, "result": {"text": f"第{index}段。"}}
                ).encode()

        def open_request(request, timeout, context=None):
            uploads.append(json.loads(request.data)["audio"])
            return Response()

        with patch("urllib.request.urlopen", open_request):
            transcript = CloudflareTranscriber(
                "account-id",
                "api-token",
                max_upload_bytes=1,
                segment_seconds=1,
            ).transcribe(
                audio_path,
                progress_callback=lambda processed, total: progress.append(
                    (round(processed), round(total))
                ),
            )

        self.assertGreaterEqual(len(uploads), 2)
        self.assertIn("第1段", transcript)
        self.assertIn(f"第{len(uploads)}段", transcript)
        self.assertEqual(progress[0], (0, 3))
        self.assertEqual(progress[-1], (3, 3))

    def test_cloudflare_default_uploads_stay_within_safe_audio_size(self):
        audio_path = Path(self.tempdir.name) / "long-source.mp3"
        audio_path.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        uploads = []
        segment_times = []

        def create_safe_segments(command, **_options):
            segment_index = command.index("-segment_time")
            segment_times.append(command[segment_index + 1])
            output_pattern = Path(command[-1])
            for index in range(2):
                Path(str(output_pattern).replace("%05d", f"{index:05d}")).write_bytes(
                    b"s" * (1024 * 1024)
                )

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(
                    {"success": True, "result": {"text": "安全分段。"}}
                ).encode()

        def open_request(request, timeout, context=None):
            uploads.append(base64.b64decode(json.loads(request.data)["audio"]))
            return Response()

        with patch("subprocess.run", create_safe_segments), patch(
            "urllib.request.urlopen", open_request
        ):
            CloudflareTranscriber("account-id", "api-token").transcribe(audio_path)

        self.assertEqual(segment_times, ["180"])
        self.assertEqual(len(uploads), 2)
        self.assertTrue(all(len(upload) <= 2 * 1024 * 1024 for upload in uploads))

    def test_cloudflare_keeps_small_compressed_audio_in_one_request(self):
        audio_path = Path(self.tempdir.name) / "compressed-long.mp3"
        audio_path.write_bytes(b"small compressed audio")
        uploads = []

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(
                    {"success": True, "result": {"text": "整段完整文字。"}}
                ).encode()

        def open_request(request, timeout, context=None):
            uploads.append(base64.b64decode(json.loads(request.data)["audio"]))
            return Response()

        with patch(
            "vtn.adapters.transcription._probe_audio_duration",
            return_value=75,
        ), patch(
            "subprocess.run",
            side_effect=AssertionError("small audio must not be segmented"),
        ), patch(
            "urllib.request.urlopen", open_request
        ):
            transcript = CloudflareTranscriber(
                "account-id", "api-token"
            ).transcribe(audio_path)

        self.assertEqual(len(uploads), 1)
        self.assertEqual(transcript, "整段完整文字。")

    def test_parser_completes_without_llm_configuration(self):
        workflow = ParserWorkflow(
            self.repo,
            FakePlatformMedia(),
            FakeTranscriber("完整逐字稿"),
            run_in_background=False,
        )
        task = workflow.start_parse("browser-1", "https://www.bilibili.com/video/BV1TEST")
        self.assertEqual(task["state"], "completed")
        record = self.repo.get_parser_record(task["record_id"])
        self.assertEqual(record["platform"], "bilibili")
        self.assertEqual(record["transcript_text"], "完整逐字稿")
        self.assertEqual(record["transcript_format_version"], 2)
        self.assertEqual([event.seq for event in workflow.subscribe(task["id"], 0)], [1, 2, 3, 4, 5, 6])

    def test_metadata_only_parse_does_not_download_or_transcribe(self):
        class MetadataOnlyMedia(FakePlatformMedia):
            def download_audio(self, _url, _directory):
                raise AssertionError("metadata-only parsing must not download audio")

        class MetadataOnlyTranscriber(FakeTranscriber):
            def transcribe(self, _audio_path):
                raise AssertionError("metadata-only parsing must not transcribe")

        workflow = ParserWorkflow(
            self.repo,
            MetadataOnlyMedia(),
            MetadataOnlyTranscriber(),
            run_in_background=False,
        )

        task = workflow.start_parse(
            "browser-1",
            "https://www.bilibili.com/video/BV1TEST",
            include_transcript=False,
        )
        record = self.repo.get_parser_record(task["record_id"])

        self.assertEqual(task["state"], "completed")
        self.assertEqual(task["operation"], "metadata")
        self.assertEqual(record["transcript_text"], "")
        stages = [
            event.payload.get("stage")
            for event in workflow.subscribe(task["id"], 0)
            if event.payload.get("stage")
        ]
        self.assertEqual(stages, ["resolve", "save"])

    def test_transcription_task_uses_selected_provider_and_updates_record(self):
        providers = []
        expected_transcript = "云端生成的高质量逐字稿。" * 60

        class SelectableTranscriber(FakeTranscriber):
            def transcribe_with_provider(self, _audio_path, provider):
                providers.append(provider)
                return expected_transcript

        workflow = ParserWorkflow(
            self.repo,
            FakePlatformMedia(),
            SelectableTranscriber(),
            run_in_background=False,
        )
        parse_task = workflow.start_parse(
            "browser-1",
            "https://www.bilibili.com/video/BV1TEST",
            include_transcript=False,
        )

        task = workflow.start_transcription(
            "browser-1", parse_task["record_id"], "cloudflare"
        )
        record = self.repo.get_parser_record(parse_task["record_id"])

        self.assertEqual(task["state"], "completed")
        self.assertEqual(task["operation"], "transcription")
        self.assertEqual(task["transcription_provider"], "cloudflare")
        self.assertEqual(providers, ["cloudflare"])
        self.assertEqual(record["transcript_text"], expected_transcript)

    def test_transcription_task_persists_real_audio_progress(self):
        expected_transcript = "真实进度对应完整逐字稿。" * 60

        class ProgressTranscriber(FakeTranscriber):
            def transcribe_with_provider(
                self,
                _audio_path,
                provider,
                *,
                progress_callback=None,
            ):
                self.assertEqual(provider, "local")
                progress_callback(0, 600)
                progress_callback(180, 600)
                progress_callback(420, 600)
                progress_callback(600, 600)
                return expected_transcript

        transcriber = ProgressTranscriber()
        transcriber.assertEqual = self.assertEqual
        workflow = ParserWorkflow(
            self.repo,
            FakePlatformMedia(),
            transcriber,
            run_in_background=False,
        )
        parsed = workflow.start_parse(
            "browser-1",
            "https://www.bilibili.com/video/BV1TEST",
            include_transcript=False,
        )

        task = workflow.start_transcription(
            "browser-1",
            parsed["record_id"],
            "local",
        )
        progress_events = [
            event.payload
            for event in workflow.subscribe(task["id"], 0)
            if event.event_type == "progress"
        ]

        self.assertEqual(
            [event["transcription_percent"] for event in progress_events],
            [0, 30, 70, 100],
        )
        self.assertEqual(progress_events[1]["processed_seconds"], 180)
        self.assertEqual(progress_events[1]["total_seconds"], 600)

    def test_incomplete_cloud_regeneration_keeps_existing_transcript(self):
        original_transcript = "这是原本完整的逐字稿。" * 80

        class TruncatedCloudTranscriber(FakeTranscriber):
            def transcribe_with_provider(self, _audio_path, provider):
                self.assertEqual(provider, "cloudflare")
                return "只返回了开头的一小段文字。"

        transcriber = TruncatedCloudTranscriber()
        transcriber.assertEqual = self.assertEqual
        workflow = ParserWorkflow(
            self.repo,
            FakePlatformMedia(),
            transcriber,
            run_in_background=False,
        )
        parsed = workflow.start_parse(
            "browser-1",
            "https://www.bilibili.com/video/BV1TEST",
            include_transcript=False,
        )
        self.repo.update_parser_record(
            parsed["record_id"], transcript_text=original_transcript
        )

        task = workflow.start_transcription(
            "browser-1",
            parsed["record_id"],
            "cloudflare",
            replace_existing=True,
        )
        record = self.repo.get_parser_record(parsed["record_id"])

        self.assertEqual(task["state"], "failed")
        self.assertEqual(task["error_code"], "TRANSCRIPTION_INCOMPLETE")
        self.assertTrue(task["error_retryable"])
        self.assertEqual(record["transcript_text"], original_transcript)

    def test_failed_parser_can_retry_and_preserves_stable_error(self):
        media = FakePlatformMedia(fail_once=True)
        workflow = ParserWorkflow(
            self.repo, media, FakeTranscriber(), run_in_background=False
        )
        task = workflow.start_parse("browser-1", "https://example.test/video")
        self.assertEqual(task["state"], "failed")
        self.assertEqual(task["error_code"], "MEDIA_RESOLVE_FAILED")
        retried = workflow.command(task["id"], "retry")
        self.assertEqual(retried["state"], "completed")

    def test_parser_task_hides_stored_media_resolver_internals(self):
        class LeakyMedia(FakePlatformMedia):
            def resolve(self, _url):
                raise DomainError(
                    "MEDIA_RESOLVE_FAILED",
                    '视频解析失败：could not find cookies in "/opt/private/chrome"',
                    retryable=True,
                )

        workflow = ParserWorkflow(
            self.repo, LeakyMedia(), FakeTranscriber(), run_in_background=False
        )

        task = workflow.start_parse(
            "browser-1", "https://www.bilibili.com/video/BV1TEST"
        )

        self.assertEqual(task["error_code"], "MEDIA_RESOLVE_FAILED")
        self.assertEqual(
            task["error_message"],
            "视频解析失败：视频平台暂时拒绝解析，可能需要登录凭证或链接已失效",
        )
        self.assertNotIn("/opt/", task["error_message"])

    def test_transcription_failure_clears_stale_progress_and_reports_retryability(self):
        class TimedOutTranscriber(FakeTranscriber):
            def transcribe(self, audio_path):
                raise DomainError(
                    "TRANSCRIPTION_UPLOAD_TIMEOUT",
                    "Cloudflare 音频上传超时，已停止本次解析，请检查网络后重试。",
                    retryable=True,
                )

        workflow = ParserWorkflow(
            self.repo, FakePlatformMedia(), TimedOutTranscriber(), run_in_background=False
        )

        task = workflow.start_parse("browser-1", "https://example.test/video")
        error_event = workflow.subscribe(task["id"], 0)[-1]

        self.assertEqual(task["state"], "failed")
        self.assertEqual(task["progress"], {})
        self.assertEqual(task["error_code"], "TRANSCRIPTION_UPLOAD_TIMEOUT")
        self.assertTrue(error_event.payload["retryable"])

    def test_parser_reports_each_real_processing_stage_in_order(self):
        workflow = ParserWorkflow(
            self.repo, FakePlatformMedia(), FakeTranscriber(), run_in_background=False
        )

        task = workflow.start_parse("browser-1", "https://example.test/video")
        events = workflow.subscribe(task["id"], 0)
        stages = [event.payload.get("stage") for event in events if event.payload.get("stage")]

        self.assertEqual(stages, ["resolve", "download", "transcribe", "save"])
        self.assertEqual(task["progress"], {"stage": "complete", "label": "解析完成", "percent": 100})

    def test_shared_heavy_task_lock_serializes_parser_and_note_workflows(self):
        parser_entered = threading.Event()
        release_parser = threading.Event()
        note_entered = threading.Event()
        heavy_task_lock = threading.Lock()

        class BlockingTranscriber(FakeTranscriber):
            def transcribe(self, _audio_path):
                parser_entered.set()
                if not release_parser.wait(2):
                    raise AssertionError("测试没有释放解析任务")
                return "解析逐字稿"

        class ObservedLLM(FakeLLM):
            def analyze(self, transcript, request_text):
                note_entered.set()
                return super().analyze(transcript, request_text)

        parser = ParserWorkflow(
            self.repo,
            FakePlatformMedia(),
            BlockingTranscriber(),
            heavy_task_lock=heavy_task_lock,
        )
        notes = NoteWorkflow(
            self.repo, ObservedLLM(), heavy_task_lock=heavy_task_lock
        )

        parser_task = parser.start_parse("browser-1", "https://example.test/parser")
        self.assertTrue(parser_entered.wait(1))
        note_task = notes.start_analysis({
            "device_id": "browser-1",
            "source": {
                "type": "paste", "name": "并发测试", "transcript": "笔记逐字稿",
            },
        })
        time.sleep(0.1)
        self.assertFalse(note_entered.is_set())

        release_parser.set()
        self.assertTrue(note_entered.wait(1))
        for _ in range(100):
            if (
                parser.get_task(parser_task["id"])["state"] == "completed"
                and notes.get_task(note_task["id"])["state"] == "recommendation_ready"
            ):
                break
            time.sleep(0.01)
        self.assertEqual(parser.get_task(parser_task["id"])["state"], "completed")
        self.assertEqual(notes.get_task(note_task["id"])["state"], "recommendation_ready")

    def test_bilibili_failure_skips_missing_browser_cookie_and_hides_server_paths(self):
        calls = []

        def fail_without_credentials(args, **_options):
            calls.append(args)
            raise subprocess.CalledProcessError(
                1,
                args,
                stderr=(
                    'ERROR: could not find chrome cookies database in '
                    '"/opt/video-to-notes/.config/google-chrome"'
                ),
            )

        with patch.dict("os.environ", {"HOME": self.tempdir.name}), patch(
            "subprocess.run", fail_without_credentials
        ), patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("测试中禁用外部请求"),
        ):
            media = YtDlpPlatformMedia()
            with self.assertRaises(DomainError) as context:
                media.resolve("https://www.bilibili.com/video/BV1zR4xzRECc")

        self.assertEqual(len(calls), 1)
        self.assertNotIn("--cookies-from-browser", calls[0])
        self.assertEqual(context.exception.code, "MEDIA_RESOLVE_FAILED")
        self.assertEqual(
            context.exception.message,
            "视频解析失败：视频平台暂时拒绝解析，可能需要登录凭证或链接已失效",
        )
        self.assertNotIn("/opt/", context.exception.message)

    def test_douyin_link_formats_are_detected(self):
        urls = (
            "https://www.douyin.com/video/7253815894357363979",
            "https://v.douyin.com/ieYvXhHW",
            "https://www.iesdouyin.com/share/video/7267477691337624895/",
            "https://jx.douyin.com/iLxdnwwN",
            "https://www.douyin.com/discover?modal_id=7255485257351269644",
        )

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(detect_platform(url), "douyin")

    def test_media_adapter_prefers_project_virtualenv_tools(self):
        media = YtDlpPlatformMedia()

        self.assertEqual(
            media.env["PATH"].split(":", 1)[0],
            str(Path(sys.executable).parent),
        )

    def test_douyin_desktop_and_share_urls_are_normalized_to_video_url(self):
        media = YtDlpPlatformMedia()

        self.assertEqual(
            media._normalize_source_url(
                "https://www.douyin.com/discover?modal_id=7255485257351269644"
            ),
            "https://www.douyin.com/video/7255485257351269644",
        )
        self.assertEqual(
            media._normalize_source_url(
                "https://www.iesdouyin.com/share/video/7267477691337624895/"
            ),
            "https://www.douyin.com/video/7267477691337624895",
        )

    def test_douyin_short_url_is_resolved_before_ytdlp(self):
        class RedirectResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def geturl(self):
                return "https://www.douyin.com/video/7253815894357363979"

        media = YtDlpPlatformMedia()
        with patch("urllib.request.urlopen", return_value=RedirectResponse()) as open_url:
            normalized = media._normalize_source_url(
                "https://v.douyin.com/ieYvXhHW"
            )

        self.assertEqual(
            normalized,
            "https://www.douyin.com/video/7253815894357363979",
        )
        self.assertEqual(open_url.call_args.kwargs["timeout"], 20)

    def test_douyin_cookie_attempts_prefer_configured_file_then_browser(self):
        cookie_file = Path(self.tempdir.name) / "douyin-cookies.txt"
        cookie_file.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
        chrome_cookie_db = (
            Path(self.tempdir.name)
            / "Library/Application Support/Google/Chrome/Default/Network/Cookies"
        )
        chrome_cookie_db.parent.mkdir(parents=True)
        chrome_cookie_db.write_bytes(b"fixture")

        with patch.dict(
            "os.environ",
            {
                "HOME": self.tempdir.name,
                "VTN_DOUYIN_COOKIES_PATH": str(cookie_file),
            },
        ):
            attempts = YtDlpPlatformMedia()._cookie_attempts(
                "https://www.douyin.com/video/7253815894357363979"
            )

        self.assertEqual(
            attempts,
            [
                ["--cookies", str(cookie_file)],
                ["--cookies-from-browser", "chrome"],
                [],
            ],
        )

    def test_douyin_resolve_uses_normalized_url_and_configured_cookie_file(self):
        cookie_file = Path(self.tempdir.name) / "douyin-cookies.txt"
        cookie_file.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
        calls = []

        def resolve_video(args, **_options):
            calls.append(args)
            return types.SimpleNamespace(
                stdout=json.dumps(
                    {
                        "title": "遇见好看的晚霞",
                        "uploader": "79106552719",
                        "channel": "测试作者",
                        "description": "抖音公开作品",
                        "duration": 19,
                        "thumbnail": "https://example.test/douyin.jpg",
                    },
                    ensure_ascii=False,
                )
            )

        with patch.dict(
            "os.environ",
            {
                "HOME": self.tempdir.name,
                "VTN_DOUYIN_COOKIES_PATH": str(cookie_file),
            },
        ), patch("subprocess.run", resolve_video):
            metadata = YtDlpPlatformMedia().resolve(
                "https://www.douyin.com/discover?modal_id=7253815894357363979"
            )

        self.assertEqual(metadata["platform"], "douyin")
        self.assertEqual(metadata["creator"], "测试作者")
        self.assertEqual(metadata["source_url"], "https://www.douyin.com/discover?modal_id=7253815894357363979")
        self.assertIn("--cookies", calls[0])
        self.assertEqual(
            calls[0][-1],
            "https://www.douyin.com/video/7253815894357363979",
        )

    def test_douyin_server_missing_fresh_cookie_tells_user_to_contact_admin(self):
        def reject_without_fresh_cookie(args, **_options):
            raise subprocess.CalledProcessError(
                1,
                args,
                stderr="ERROR: Fresh cookies (not necessarily logged in) are needed",
            )

        with patch.dict(
            "os.environ",
            {"HOME": self.tempdir.name, "VTN_DOUYIN_COOKIES_PATH": ""},
        ), patch("subprocess.run", reject_without_fresh_cookie):
            with self.assertRaises(DomainError) as context:
                YtDlpPlatformMedia().resolve(
                    "https://www.douyin.com/video/7253815894357363979"
                )

        self.assertEqual(context.exception.code, "DOUYIN_ACCESS_REQUIRED")
        self.assertEqual(
            context.exception.message,
            "服务器抖音解析凭证暂不可用，请联系管理员更新后再重试。",
        )
        self.assertTrue(context.exception.retryable)

    def test_douyin_local_missing_fresh_cookie_still_suggests_opening_chrome(self):
        chrome_cookie_db = (
            Path(self.tempdir.name)
            / "Library/Application Support/Google/Chrome/Default/Network/Cookies"
        )
        chrome_cookie_db.parent.mkdir(parents=True)
        chrome_cookie_db.write_bytes(b"fixture")

        def reject_without_fresh_cookie(args, **_options):
            raise subprocess.CalledProcessError(
                1,
                args,
                stderr="ERROR: Fresh cookies (not necessarily logged in) are needed",
            )

        with patch.dict(
            "os.environ",
            {"HOME": self.tempdir.name, "VTN_DOUYIN_COOKIES_PATH": ""},
        ), patch("subprocess.run", reject_without_fresh_cookie):
            with self.assertRaises(DomainError) as context:
                YtDlpPlatformMedia().resolve(
                    "https://www.douyin.com/video/7253815894357363979"
                )

        self.assertEqual(context.exception.code, "DOUYIN_ACCESS_REQUIRED")
        self.assertEqual(
            context.exception.message,
            "抖音解析凭证已失效，请先在 Chrome 打开一次抖音后再重试。",
        )
        self.assertTrue(context.exception.retryable)

    def test_bilibili_resolve_uses_public_api_when_webpage_is_blocked(self):
        def blocked_webpage(args, **_options):
            raise subprocess.CalledProcessError(
                1,
                args,
                stderr="ERROR: HTTP Error 412: Precondition Failed",
            )

        api_response = {
            "code": 0,
            "data": {
                "title": "公开 API 视频标题",
                "owner": {"name": "公开视频作者"},
                "desc": "公开视频简介",
                "duration": 1314,
                "pic": "https://example.test/cover.jpg",
                "cid": 123456,
            },
        }

        with patch("subprocess.run", blocked_webpage), patch(
            "urllib.request.urlopen",
            return_value=io.BytesIO(json.dumps(api_response).encode("utf-8")),
        ):
            result = YtDlpPlatformMedia().resolve(
                "https://www.bilibili.com/video/BV1zR4xzRECc"
            )

        self.assertEqual(
            result,
            {
                "source_url": "https://www.bilibili.com/video/BV1zR4xzRECc",
                "platform": "bilibili",
                "title": "公开 API 视频标题",
                "creator": "公开视频作者",
                "description": "公开视频简介",
                "duration_seconds": 1314,
                "thumbnail_url": "https://example.test/cover.jpg",
            },
        )

    def test_bilibili_audio_uses_public_api_when_webpage_download_is_blocked(self):
        def blocked_webpage(args, **_options):
            raise subprocess.CalledProcessError(
                1,
                args,
                stderr="ERROR: HTTP Error 412: Precondition Failed",
            )

        view_response = {
            "code": 0,
            "data": {"cid": 123456},
        }
        play_response = {
            "code": 0,
            "data": {
                "dash": {
                    "audio": [
                        {
                            "bandwidth": 128000,
                            "baseUrl": "https://audio.bilivideo.com/fixture.m4s",
                        }
                    ]
                }
            },
        }

        def open_public_resource(request, timeout):
            if "web-interface/view" in request.full_url:
                return io.BytesIO(json.dumps(view_response).encode("utf-8"))
            if "player/playurl" in request.full_url:
                return io.BytesIO(json.dumps(play_response).encode("utf-8"))
            return io.BytesIO(b"fixture-bilibili-audio")

        with patch("subprocess.run", blocked_webpage), patch(
            "urllib.request.urlopen", open_public_resource
        ):
            path = YtDlpPlatformMedia().download_audio(
                "https://www.bilibili.com/video/BV1zR4xzRECc",
                Path(self.tempdir.name),
            )

        self.assertEqual(path.name, "audio.m4a")
        self.assertEqual(path.read_bytes(), b"fixture-bilibili-audio")

    def test_bilibili_video_uses_public_api_when_webpage_download_is_blocked(self):
        def run_media_command(args, **_options):
            if args[0] == "yt-dlp":
                raise subprocess.CalledProcessError(
                    1,
                    args,
                    stderr="ERROR: HTTP Error 412: Precondition Failed",
                )
            if args[0] == "ffmpeg":
                Path(args[-1]).write_bytes(b"fixture-merged-mp4")
                return types.SimpleNamespace(returncode=0)
            raise AssertionError(f"未预期的外部命令：{args[0]}")

        view_response = {"code": 0, "data": {"cid": 123456}}
        play_response = {
            "code": 0,
            "data": {
                "dash": {
                    "video": [
                        {
                            "bandwidth": 800000,
                            "codecs": "avc1.640032",
                            "baseUrl": "https://video.bilivideo.com/fixture.m4s",
                        }
                    ],
                    "audio": [
                        {
                            "bandwidth": 128000,
                            "baseUrl": "https://audio.bilivideo.com/fixture.m4s",
                        }
                    ],
                }
            },
        }

        def open_public_resource(request, timeout):
            if "web-interface/view" in request.full_url:
                return io.BytesIO(json.dumps(view_response).encode("utf-8"))
            if "player/playurl" in request.full_url:
                return io.BytesIO(json.dumps(play_response).encode("utf-8"))
            if request.full_url.startswith("https://video.bilivideo.com/"):
                return io.BytesIO(b"fixture-video-stream")
            if request.full_url.startswith("https://audio.bilivideo.com/"):
                return io.BytesIO(b"fixture-audio-stream")
            raise AssertionError(f"未预期的外部请求：{request.full_url}")

        with patch("subprocess.run", run_media_command), patch(
            "urllib.request.urlopen",
            open_public_resource,
        ):
            path = YtDlpPlatformMedia().download_video(
                "https://www.bilibili.com/video/BV1zR4xzRECc",
                Path(self.tempdir.name),
            )

        self.assertEqual(path.name, "video.mp4")
        self.assertEqual(path.read_bytes(), b"fixture-merged-mp4")

    def test_xiaohongshu_resolve_enriches_missing_creator_nickname(self):
        def run_command(args, **_options):
            if args[0] == "yt-dlp":
                return types.SimpleNamespace(
                    stdout=json.dumps(
                        {
                            "title": "拯救你AI审美的5个宝藏网站",
                            "uploader": None,
                            "uploader_id": "640c29eb000000001001c91b",
                            "thumbnail": "https://example.test/xhs-cover.jpg",
                            "webpage_url": (
                                "https://www.xiaohongshu.com/discovery/item/"
                                "6a6821f600000000090369c3?xsec_token=test-token"
                            ),
                        },
                        ensure_ascii=False,
                    )
                )
            if args[0] == "xhs":
                return types.SimpleNamespace(
                    stdout=json.dumps(
                        {
                            "data": {
                                "items": [
                                    {
                                        "note_card": {
                                            "user": {
                                                "nickname": "AI教练振轩",
                                                "user_id": "640c29eb000000001001c91b",
                                            }
                                        }
                                    }
                                ]
                            }
                        },
                        ensure_ascii=False,
                    )
                )
            raise AssertionError(f"未预期的外部命令：{args[0]}")

        with patch("subprocess.run", run_command):
            metadata = YtDlpPlatformMedia().resolve(
                "http://xhslink.cn/o/4W5MlG9aJai"
            )

        self.assertEqual(metadata["platform"], "xiaohongshu")
        self.assertEqual(metadata["creator"], "AI教练振轩")

    def test_note_task_keeps_the_llm_profile_selected_when_it_started(self):
        class BoundLLM(FakeLLM):
            def __init__(self, profile_id):
                super().__init__()
                self.profile_id = profile_id

            def generate_direct(self, task):
                result = super().generate_direct(task)
                result["chapters"][0]["content_markdown"] += (
                    f"\n\n任务模型：{self.profile_id}"
                )
                return result

        class RoutedLLM(FakeLLM):
            def __init__(self):
                super().__init__()
                self.active = "deepseek-profile"

            def active_profile_id(self):
                return self.active

            def for_profile(self, profile_id):
                return BoundLLM(profile_id)

        llm = RoutedLLM()
        workflow = NoteWorkflow(
            self.repo,
            llm,
            run_in_background=False,
        )
        task = workflow.start_analysis(
            {
                "source": {
                    "type": "paste",
                    "transcript": "这是一段用于验证模型切换边界的逐字稿。",
                }
            }
        )
        self.assertEqual(task["llm_profile_id"], "deepseek-profile")

        llm.active = "openrouter-profile"
        completed = workflow.command(task["id"], {"type": "start_generation"})
        note = self.repo.get_note(completed["note_id"])

        self.assertIn("任务模型：deepseek-profile", note["current_markdown"])
        self.assertNotIn("任务模型：openrouter-profile", note["current_markdown"])

    def test_note_task_binds_the_profile_for_the_user_selected_route(self):
        class BoundLLM(FakeLLM):
            def __init__(self, profile_id):
                super().__init__()
                self.profile_id = profile_id

            def generate_direct(self, task):
                result = super().generate_direct(task)
                result["chapters"][0]["content_markdown"] += f"\n\n任务模型：{self.profile_id}"
                return result

        class RoutedLLM(FakeLLM):
            def profile_id_for_channel(self, channel):
                return f"{channel}-profile"

            def for_profile(self, profile_id):
                return BoundLLM(profile_id)

        workflow = NoteWorkflow(self.repo, RoutedLLM(), run_in_background=False)
        task = workflow.start_analysis(
            {
                "generation_route": "free",
                "source": {
                    "type": "paste",
                    "transcript": "这是一段用于验证用户选择免费线路的逐字稿。",
                },
            }
        )

        self.assertEqual(task["generation_route"], "free")
        self.assertEqual(task["llm_profile_id"], "free-profile")
        completed = workflow.command(task["id"], {"type": "start_generation"})
        note = self.repo.get_note(completed["note_id"])
        self.assertIn("任务模型：free-profile", note["current_markdown"])

    def test_xiaohongshu_short_link_enriches_creator_after_redirect(self):
        short_url = "http://xhslink.cn/o/4W5MlG9aJai"

        class RedirectResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def geturl(self):
                return (
                    "https://www.xiaohongshu.com/discovery/item/"
                    "6a6821f600000000090369c3?xsec_token=redirect-token"
                )

        def run_command(args, **_options):
            if args[0] == "yt-dlp":
                return types.SimpleNamespace(
                    stdout=json.dumps(
                        {
                            "title": "小红书短链接视频",
                            "uploader": None,
                            "thumbnail": "https://example.test/xhs-cover.jpg",
                            "webpage_url": short_url,
                        },
                        ensure_ascii=False,
                    )
                )
            if args[0] == "xhs":
                return types.SimpleNamespace(
                    stdout=json.dumps(
                        {
                            "data": {
                                "items": [
                                    {
                                        "note_card": {
                                            "user": {"nickname": "短链接作者"}
                                        }
                                    }
                                ]
                            }
                        },
                        ensure_ascii=False,
                    )
                )
            raise AssertionError(f"未预期的外部命令：{args[0]}")

        with patch("subprocess.run", run_command), patch(
            "urllib.request.urlopen",
            return_value=RedirectResponse(),
        ):
            metadata = YtDlpPlatformMedia().resolve(short_url)

        self.assertEqual(metadata["creator"], "短链接作者")

    def test_xiaohongshu_short_link_uses_page_author_when_xhs_cli_is_unavailable(self):
        short_url = "http://xhslink.cn/o/4W5MlG9aJai"
        uploader_id = "640c29eb000000001001c91b"

        class PageResponse(io.BytesIO):
            def geturl(self):
                return (
                    "https://www.xiaohongshu.com/discovery/item/"
                    "6a6821f600000000090369c3?xsec_token=redirect-token"
                )

        def run_command(args, **_options):
            if args[0] == "yt-dlp":
                return types.SimpleNamespace(
                    stdout=json.dumps(
                        {
                            "title": "小红书页面作者回退",
                            "uploader": None,
                            "uploader_id": uploader_id,
                            "thumbnail": "https://example.test/xhs-cover.jpg",
                            "webpage_url": short_url,
                        },
                        ensure_ascii=False,
                    )
                )
            if args[0] == "xhs":
                raise FileNotFoundError("xhs is not installed")
            raise AssertionError(f"未预期的外部命令：{args[0]}")

        page = (
            '{"user":{"userId":"another-user","nickname":"其他用户"}},'
            f'{{"user":{{"userId":"{uploader_id}","nickname":"页面真实作者"}}}}'
        ).encode()
        with patch("subprocess.run", run_command), patch(
            "urllib.request.urlopen",
            return_value=PageResponse(page),
        ):
            metadata = YtDlpPlatformMedia().resolve(short_url)

        self.assertEqual(metadata["creator"], "页面真实作者")

    def test_xiaohongshu_final_url_uses_page_author_when_xhs_cli_is_unavailable(self):
        final_url = (
            "https://www.xiaohongshu.com/discovery/item/"
            "6a6821f600000000090369c3?xsec_token=redirect-token"
        )
        uploader_id = "640c29eb000000001001c91b"

        def run_command(args, **_options):
            if args[0] == "yt-dlp":
                return types.SimpleNamespace(
                    stdout=json.dumps(
                        {
                            "title": "小红书最终地址作者回退",
                            "uploader": None,
                            "uploader_id": uploader_id,
                            "thumbnail": "https://example.test/xhs-cover.jpg",
                            "webpage_url": final_url,
                        },
                        ensure_ascii=False,
                    )
                )
            if args[0] == "xhs":
                raise FileNotFoundError("xhs is not installed")
            raise AssertionError(f"未预期的外部命令：{args[0]}")

        page = (
            f'{{"user":{{"userId":"{uploader_id}",'
            '"nickname":"最终页面作者"}}}'
        ).encode()
        with patch("subprocess.run", run_command), patch(
            "urllib.request.urlopen",
            return_value=io.BytesIO(page),
        ):
            metadata = YtDlpPlatformMedia().resolve(final_url)

        self.assertEqual(metadata["creator"], "最终页面作者")

    def test_xiaohongshu_uses_public_profile_when_note_page_is_blocked(self):
        final_url = (
            "https://www.xiaohongshu.com/discovery/item/"
            "6a6821f600000000090369c3?xsec_token=redirect-token"
        )
        uploader_id = "640c29eb000000001001c91b"

        def run_command(args, **_options):
            if args[0] == "yt-dlp":
                return types.SimpleNamespace(
                    stdout=json.dumps(
                        {
                            "title": "小红书作者主页回退",
                            "uploader": None,
                            "uploader_id": uploader_id,
                            "thumbnail": "https://example.test/xhs-cover.jpg",
                            "webpage_url": final_url,
                        },
                        ensure_ascii=False,
                    )
                )
            if args[0] == "xhs":
                raise FileNotFoundError("xhs is not installed")
            raise AssertionError(f"未预期的外部命令：{args[0]}")

        def open_xiaohongshu_page(request, timeout):
            if "/user/profile/" in request.full_url:
                return io.BytesIO(
                    (
                        f'{{"userId":"{uploader_id}",'
                        '"nickname":"作者主页昵称"}'
                    ).encode()
                )
            return io.BytesIO(b"<html>website login error</html>")

        with patch("subprocess.run", run_command), patch(
            "urllib.request.urlopen",
            open_xiaohongshu_page,
        ):
            metadata = YtDlpPlatformMedia().resolve(final_url)

        self.assertEqual(metadata["creator"], "作者主页昵称")

    def test_xiaohongshu_uses_ytdlp_page_data_when_public_pages_require_login(self):
        note_id = "6a6821f600000000090369c3"
        uploader_id = "640c29eb000000001001c91b"
        final_url = (
            "https://www.xiaohongshu.com/discovery/item/"
            f"{note_id}?xsec_token=redirect-token"
        )

        def run_command(args, **_options):
            if args[0] == "yt-dlp":
                return types.SimpleNamespace(
                    stdout=json.dumps(
                        {
                            "id": note_id,
                            "title": "小红书登录拦截作者回退",
                            "uploader": None,
                            "uploader_id": uploader_id,
                            "thumbnail": "https://example.test/xhs-cover.jpg",
                            "webpage_url": final_url,
                        },
                        ensure_ascii=False,
                    )
                )
            if args[0] == "xhs":
                raise FileNotFoundError("xhs is not installed")
            raise AssertionError(f"未预期的外部命令：{args[0]}")

        login_page = io.BytesIO(b"<html>website login required</html>")
        initial_state_page = (
            "<script>window.__INITIAL_STATE__="
            + json.dumps(
                {
                    "note": {
                        "noteDetailMap": {
                            note_id: {
                                "note": {
                                    "user": {
                                        "userId": uploader_id,
                                        "nickname": "yt-dlp页面真实作者",
                                    }
                                }
                            }
                        }
                    }
                },
                ensure_ascii=False,
            )
            + "</script>"
        )
        with patch("subprocess.run", run_command), patch(
            "urllib.request.urlopen",
            side_effect=lambda *_args, **_kwargs: io.BytesIO(login_page.getvalue()),
        ), patch(
            "yt_dlp.extractor.xiaohongshu.XiaoHongShuIE._download_webpage",
            return_value=initial_state_page,
        ):
            metadata = YtDlpPlatformMedia().resolve(final_url)

        self.assertEqual(metadata["creator"], "yt-dlp页面真实作者")

    def test_llm_ssl_context_requires_certificate_verification(self):
        context = OpenAICompatibleLLM._ssl_context()
        self.assertNotEqual(context.verify_mode, 0)
        self.assertTrue(context.check_hostname)

    def test_realistic_llm_recommendation_shape_is_normalized(self):
        normalized = OpenAICompatibleLLM._normalize_recommendation(
            {
                "title": "亲密关系中的控制欲：成因与解决",
                "reason": "适合完整笔记",
                "structure": {
                    "option_ids": ["problem_solution", "thematic"],
                    "recommended_id": "problem_solution",
                },
                "detail": {"recommended_id": "complete"},
                "method": {"recommended_id": "outline"},
                "modules": {"recommended_ids": ["summary", "unknown"]},
            }
        )
        self.assertEqual(normalized["detail"]["recommended_id"], "complete")
        self.assertEqual(normalized["method"]["recommended_id"], "outline")
        self.assertEqual(normalized["modules"]["recommended_ids"], ["summary"])
        self.assertIsInstance(normalized["structure"], dict)
        self.assertEqual(normalized["structure"]["options"][0]["id"], "problem_solution")

    def test_llm_can_recommend_body_only_without_extra_modules(self):
        normalized = OpenAICompatibleLLM._normalize_recommendation(
            {
                "title": "Skill 开发与应用入门",
                "reason": "正文已经能够完整承载本次学习目标。",
                "modules": {"recommended_ids": [], "reasons": {}},
            }
        )

        self.assertEqual(normalized["modules"]["recommended_ids"], [])

    def test_pre_read_can_phrase_the_four_decisions_for_this_transcript(self):
        normalized = OpenAICompatibleLLM._normalize_recommendation(
            {
                "title": "Skill 开发与应用入门",
                "reason": "这是一堂从背景逐步走向实操的长课程。",
                "structure": {
                    "question": "要不要沿着讲师从背景到实操的路线来整理？",
                    "options": [
                        {
                            "id": "source_flow",
                            "label": "沿课程推进",
                            "reason": "保留背景、原理、工具、实操和作业展示的递进关系。",
                        },
                        {
                            "id": "thematic",
                            "label": "按 Skill 主题重组",
                            "reason": "把定义、工具和实践分别归类。",
                        },
                    ],
                    "recommended_id": "source_flow",
                },
                "detail": {
                    "question": "两小时课程要保留到什么程度？",
                    "recommended_id": "key",
                    "reason": "保留关键解释、案例和有辨识度的原话。",
                },
                "method": {
                    "question": "长课程是否先确认大纲？",
                    "recommended_id": "outline",
                    "reason": "主题多，先确认章节更稳妥。",
                },
                "modules": {
                    "question": "正文之外还需要复习工具吗？",
                    "recommended_ids": [],
                    "reasons": {},
                },
            }
        )

        self.assertEqual(
            normalized["structure"]["question"],
            "要不要沿着讲师从背景到实操的路线来整理？",
        )
        self.assertEqual(normalized["structure"]["options"][0]["label"], "沿课程推进")
        self.assertEqual(
            normalized["detail"]["question"], "两小时课程要保留到什么程度？"
        )
        self.assertEqual(normalized["method"]["question"], "长课程是否先确认大纲？")
        self.assertEqual(
            normalized["modules"]["question"], "正文之外还需要复习工具吗？"
        )


if __name__ == "__main__":
    unittest.main()
