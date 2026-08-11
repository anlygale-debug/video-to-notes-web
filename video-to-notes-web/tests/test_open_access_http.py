import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from vtn.access import AccessManager, install_access_middleware
from vtn.adapters.llm import FakeLLM
from vtn.adapters.media import FakePlatformMedia
from vtn.adapters.transcription import FakeTranscriber
from vtn.documents.notes import NoteDocument
from vtn.exports.exporter import Exporter
from vtn.storage.sqlite import SQLiteRepository
from vtn.web.api import create_v3_router
from vtn.workflows.notes import NoteWorkflow
from vtn.workflows.parser import ParserWorkflow


class OpenAccessHttpTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repository = SQLiteRepository(Path(self.tempdir.name) / "open-access.sqlite3")
        self.repository.migrate()
        self.access = AccessManager(
            self.repository,
            "open-access-secret",
            secure_cookie=False,
        )
        self.invite_code = self.access.create_grant(
            "内测用户",
            transcription_seconds_limit=1800,
            note_generation_limit=5,
            max_video_seconds=1200,
        )["code"]
        llm = FakeLLM()
        parser = ParserWorkflow(
            self.repository,
            FakePlatformMedia(),
            FakeTranscriber("这是完整的测试逐字稿。" * 80),
            run_in_background=False,
            access_manager=self.access,
        )
        notes = NoteWorkflow(
            self.repository,
            llm,
            run_in_background=False,
            access_manager=self.access,
        )
        app = FastAPI()
        app.include_router(
            create_v3_router(
                self.repository,
                parser,
                notes,
                NoteDocument(self.repository, llm),
                Exporter(self.repository),
                access_manager=self.access,
            )
        )
        install_access_middleware(app, self.access)
        self.client = TestClient(app)
        self.device_headers = {"X-VTN-Device-ID": "anonymous-device-a"}

    def tearDown(self):
        self.repository.close()
        self.tempdir.cleanup()

    def _parse_metadata(self):
        response = self.client.post(
            "/api/v3/parser/tasks",
            headers=self.device_headers,
            json={
                "device_id": "anonymous-device-a",
                "source_url": "https://www.bilibili.com/video/BV1OPEN",
                "include_transcript": False,
            },
        )
        self.assertEqual(response.status_code, 202)
        task = response.json()["task"]
        self.assertEqual(task["state"], "completed", task)
        return task["record_id"]

    def test_anonymous_user_can_parse_transcribe_free_and_generate_free_notes(self):
        record_id = self._parse_metadata()

        transcription = self.client.post(
            f"/api/v3/parser/records/{record_id}/transcription-tasks",
            headers=self.device_headers,
            json={"device_id": "anonymous-device-a", "provider": "local"},
        )
        self.assertEqual(transcription.status_code, 202)
        self.assertEqual(
            transcription.json()["task"]["state"],
            "completed",
            transcription.json()["task"],
        )

        note = self.client.post(
            "/api/v3/note-tasks",
            headers=self.device_headers,
            json={
                "device_id": "anonymous-device-a",
                "generation_route": "free",
                "source": {"type": "parser", "parser_record_id": record_id},
            },
        )
        self.assertEqual(note.status_code, 202)
        self.assertEqual(note.json()["task"]["generation_route"], "free")

        status = self.client.get("/api/v3/access/status").json()
        self.assertFalse(status["authenticated"])
        self.assertIsNone(status["access"])

    def test_high_speed_requires_invite_and_keeps_browser_history_owner(self):
        record_id = self._parse_metadata()

        blocked = self.client.post(
            f"/api/v3/parser/records/{record_id}/transcription-tasks",
            headers=self.device_headers,
            json={"device_id": "anonymous-device-a", "provider": "cloudflare"},
        )
        self.assertEqual(blocked.status_code, 401)
        self.assertEqual(blocked.json()["error"]["code"], "ACCESS_REQUIRED")

        login = self.client.post(
            "/api/v3/access/login",
            json={"code": self.invite_code},
        )
        self.assertEqual(login.status_code, 200)

        transcription = self.client.post(
            f"/api/v3/parser/records/{record_id}/transcription-tasks",
            headers=self.device_headers,
            json={"device_id": "anonymous-device-a", "provider": "cloudflare"},
        )
        self.assertEqual(transcription.status_code, 202)
        self.assertEqual(
            transcription.json()["task"]["state"],
            "completed",
            transcription.json()["task"],
        )

        status = self.client.get("/api/v3/access/status").json()["access"]
        self.assertEqual(status["remaining_transcription_seconds"], 1200)
        self.assertEqual(
            self.client.get(
                f"/api/v3/parser/records/{record_id}",
                headers=self.device_headers,
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                f"/api/v3/parser/records/{record_id}",
                headers={"X-VTN-Device-ID": "anonymous-device-b"},
            ).status_code,
            404,
        )

        paid_note = self.client.post(
            "/api/v3/note-tasks",
            headers=self.device_headers,
            json={
                "device_id": "anonymous-device-a",
                "generation_route": "paid",
                "source": {"type": "parser", "parser_record_id": record_id},
            },
        )
        self.assertEqual(paid_note.status_code, 202)
        status = self.client.get("/api/v3/access/status").json()["access"]
        self.assertEqual(status["remaining_high_speed_generations"], 4)

    def test_anonymous_user_cannot_start_high_speed_notes(self):
        response = self.client.post(
            "/api/v3/note-tasks",
            headers=self.device_headers,
            json={
                "device_id": "anonymous-device-a",
                "generation_route": "paid",
                "source": {
                    "type": "paste",
                    "name": "匿名逐字稿",
                    "transcript": "这是一份无需内测码即可导入的逐字稿。",
                },
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "ACCESS_REQUIRED")


if __name__ == "__main__":
    unittest.main()
