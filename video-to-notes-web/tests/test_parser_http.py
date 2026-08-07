import asyncio
import tempfile
import time
import unittest
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vtn.adapters.media import FakePlatformMedia
from vtn.adapters.transcription import FakeTranscriber
from vtn.domain.errors import DomainError
from vtn.storage.sqlite import SQLiteRepository
from vtn.web.api import create_v3_router
from vtn.workflows.parser import ParserWorkflow


class ParserHttpTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = SQLiteRepository(Path(self.tempdir.name) / "test.sqlite3")
        self.repo.migrate()
        self.workflow = ParserWorkflow(
            self.repo, FakePlatformMedia(), FakeTranscriber(), run_in_background=False
        )
        app = FastAPI()
        app.include_router(create_v3_router(self.repo, self.workflow))
        self.client = TestClient(app)

    def tearDown(self):
        self.repo.close()
        self.tempdir.cleanup()

    def test_parser_http_contract_and_transcript_download(self):
        response = self.client.post(
            "/api/v3/parser/tasks",
            json={"device_id": "browser", "source_url": "https://www.bilibili.com/video/BV1TEST"},
        )
        self.assertEqual(response.status_code, 202)
        task = response.json()["task"]
        record_id = task["record_id"]
        self.assertEqual(self.client.get(f"/api/v3/parser/tasks/{task['id']}").status_code, 200)
        record = self.client.get(f"/api/v3/parser/records/{record_id}").json()["record"]
        self.assertEqual(record["platform"], "bilibili")
        transcript = self.client.get(f"/api/v3/parser/records/{record_id}/transcript.txt")
        self.assertEqual(transcript.status_code, 200)
        self.assertIn("固定逐字稿", transcript.text)

    def test_xhslink_cn_task_and_record_are_identified_as_xiaohongshu(self):
        response = self.client.post(
            "/api/v3/parser/tasks",
            json={
                "device_id": "browser",
                "source_url": "http://xhslink.cn/o/4W5MlG9aJai",
            },
        )

        self.assertEqual(response.status_code, 202)
        task = response.json()["task"]
        record = self.client.get(
            f"/api/v3/parser/records/{task['record_id']}"
        ).json()["record"]

        self.assertEqual(task["platform_hint"], "xiaohongshu")
        self.assertEqual(record["platform"], "xiaohongshu")

    def test_existing_xhslink_cn_record_with_other_platform_is_presented_as_xiaohongshu(self):
        self.repo.create_parser_record(
            {
                "id": "legacy-xhs-record",
                "source_url": "http://xhslink.cn/o/4W5MlG9aJai",
                "platform": "other",
                "title": "已完成的小红书解析",
                "creator": "",
                "description": "",
                "duration_seconds": 60,
                "thumbnail_url": "",
                "transcript_text": "已保存逐字稿",
            }
        )

        detail = self.client.get(
            "/api/v3/parser/records/legacy-xhs-record"
        ).json()["record"]
        history = self.client.get("/api/v3/parser/records?limit=30").json()["items"]
        history_record = next(item for item in history if item["id"] == "legacy-xhs-record")

        self.assertEqual(detail["platform"], "xiaohongshu")
        self.assertEqual(history_record["platform"], "xiaohongshu")

    def test_video_download_uses_the_media_adapter_runtime_and_returns_an_attachment(self):
        class DownloadMedia(FakePlatformMedia):
            def download_video(self, _url, directory):
                path = directory / "video.mp4"
                path.write_bytes(b"video-fixture")
                return path

        workflow = ParserWorkflow(
            self.repo, DownloadMedia(), FakeTranscriber(), run_in_background=False
        )
        app = FastAPI()
        app.include_router(create_v3_router(self.repo, workflow))
        client = TestClient(app)
        task = client.post(
            "/api/v3/parser/tasks",
            json={"device_id": "browser", "source_url": "https://example.test/video"},
        ).json()["task"]

        response = client.get(
            f"/api/v3/parser/records/{task['record_id']}/video?download_token=ready-123"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"video-fixture")
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertTrue(response.headers["content-disposition"].endswith('.mp4"'))
        self.assertIn("vtn_download=ready-123", response.headers["set-cookie"])

    def test_video_download_reports_a_stable_error_when_the_stream_cannot_start(self):
        class BrokenVideoMedia(FakePlatformMedia):
            def video_stream_command(self, _url):
                return ["/bin/sh", "-c", "exit 1"]

            def download_video(self, _url, _directory):
                raise DomainError(
                    "MEDIA_DOWNLOAD_FAILED", "视频下载失败：测试错误", retryable=True
                )

        workflow = ParserWorkflow(
            self.repo, BrokenVideoMedia(), FakeTranscriber(), run_in_background=False
        )
        app = FastAPI()
        app.include_router(create_v3_router(self.repo, workflow))
        client = TestClient(app, raise_server_exceptions=False)
        task = client.post(
            "/api/v3/parser/tasks",
            json={"device_id": "browser", "source_url": "https://example.test/video"},
        ).json()["task"]

        response = client.get(f"/api/v3/parser/records/{task['record_id']}/video")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"]["code"], "MEDIA_DOWNLOAD_FAILED")
        self.assertIn("视频下载失败", response.json()["error"]["message"])

    def test_error_payload_is_stable(self):
        response = self.client.get("/api/v3/parser/tasks/missing")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "PARSER_TASK_NOT_FOUND")

    def test_failed_transcription_api_clears_progress_and_exposes_retryability(self):
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
        app = FastAPI()
        app.include_router(create_v3_router(self.repo, workflow))
        client = TestClient(app)

        created = client.post(
            "/api/v3/parser/tasks",
            json={"device_id": "browser", "source_url": "https://example.test/video"},
        ).json()["task"]
        task = client.get(f"/api/v3/parser/tasks/{created['id']}").json()["task"]

        self.assertEqual(task["state"], "failed")
        self.assertEqual(task["progress"], {})
        self.assertEqual(task["error_code"], "TRANSCRIPTION_UPLOAD_TIMEOUT")
        self.assertTrue(task["error_retryable"])

    def test_parser_accepts_share_text_containing_a_video_url(self):
        bilibili_url = (
            "https://www.bilibili.com/video/BV1zR4xzRECc"
            "?vd_source=eead6df7744cee5494396b8478260e72"
        )
        xhs_url = "http://xhslink.com/a/AbCdEf123"
        cases = (
            (f"【心理学：亲密关系中的控制欲破解路径】\n{bilibili_url}", bilibili_url),
            (f"复制本条信息，打开小红书查看笔记 {xhs_url} 复制后打开【小红书】", xhs_url),
        )
        for share_text, expected_url in cases:
            with self.subTest(expected_url=expected_url):
                response = self.client.post(
                    "/api/v3/parser/tasks",
                    json={"device_id": "browser", "source_url": share_text},
                )

                self.assertEqual(response.status_code, 202)
                self.assertEqual(response.json()["task"]["source_url"], expected_url)


class AsyncDownloadHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = SQLiteRepository(Path(self.tempdir.name) / "test.sqlite3")
        self.repo.migrate()

    async def asyncTearDown(self):
        self.repo.close()
        self.tempdir.cleanup()

    async def test_audio_preparation_keeps_the_app_responsive_and_returns_an_attachment(self):
        class SlowAudioMedia(FakePlatformMedia):
            def __init__(self):
                super().__init__()
                self.download_count = 0

            def download_audio(self, url, directory):
                self.download_count += 1
                if self.download_count > 1:
                    time.sleep(0.35)
                return super().download_audio(url, directory)

        workflow = ParserWorkflow(
            self.repo, SlowAudioMedia(), FakeTranscriber(), run_in_background=False
        )
        app = FastAPI()
        app.include_router(create_v3_router(self.repo, workflow))
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            task = (
                await client.post(
                    "/api/v3/parser/tasks",
                    json={"device_id": "browser", "source_url": "https://example.test/video"},
                )
            ).json()["task"]
            record_id = task["record_id"]
            started = time.perf_counter()
            audio_request = asyncio.create_task(
                client.get(
                    f"/api/v3/parser/records/{record_id}/audio?download_token=ready-456"
                )
            )
            await asyncio.sleep(0.02)

            record_response = await client.get(f"/api/v3/parser/records/{record_id}")
            responsive_after = time.perf_counter() - started
            audio_response = await audio_request

        self.assertEqual(record_response.status_code, 200)
        self.assertLess(responsive_after, 0.2)
        self.assertEqual(audio_response.status_code, 200)
        self.assertEqual(audio_response.content, b"fixture")
        self.assertIn("attachment", audio_response.headers["content-disposition"])
        self.assertIn("vtn_download=ready-456", audio_response.headers["set-cookie"])


if __name__ == "__main__":
    unittest.main()
