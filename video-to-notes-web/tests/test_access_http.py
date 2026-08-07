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
from vtn.domain.errors import DomainError
from vtn.exports.exporter import Exporter
from vtn.storage.sqlite import SQLiteRepository
from vtn.web.api import create_v3_router
from vtn.workflows.parser import ParserWorkflow
from vtn.workflows.notes import NoteWorkflow


class AccessHttpTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = SQLiteRepository(Path(self.tempdir.name) / "test.sqlite3")
        self.repo.migrate()
        self.access = AccessManager(self.repo, "test-session-secret", secure_cookie=False)
        self.code = self.access.create_grant(
            "朋友 A", transcription_seconds_limit=1800, note_generation_limit=5,
            max_video_seconds=1200,
        )["code"]
        parser = ParserWorkflow(
            self.repo, FakePlatformMedia(), FakeTranscriber(), run_in_background=False,
            access_manager=self.access,
        )
        notes = NoteWorkflow(
            self.repo, FakeLLM(), run_in_background=False, access_manager=self.access
        )
        app = FastAPI()
        app.include_router(create_v3_router(
            self.repo, parser, notes, NoteDocument(self.repo, FakeLLM()), Exporter(self.repo),
            access_manager=self.access,
        ))

        @app.get("/api/proxy-image")
        async def unsafe_legacy_image_proxy():
            return {"unsafe": True}

        install_access_middleware(app, self.access)
        self.client = TestClient(app)

    def tearDown(self):
        self.repo.close()
        self.tempdir.cleanup()

    def test_public_status_and_login_unlock_protected_api(self):
        blocked = self.client.get("/api/v3/parser/records")
        self.assertEqual(blocked.status_code, 401)
        self.assertEqual(blocked.json()["error"]["code"], "ACCESS_REQUIRED")

        login = self.client.post("/api/v3/access/login", json={"code": self.code})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json()["access"]["label"], "朋友 A")
        self.assertEqual(login.json()["access"]["remaining_transcription_seconds"], 1800)
        self.assertEqual(login.json()["access"]["remaining_note_generations"], 5)

        unlocked = self.client.get("/api/v3/parser/records")
        self.assertEqual(unlocked.status_code, 200)
        self.assertEqual(unlocked.json()["items"], [])

    def test_invalid_code_does_not_create_a_session(self):
        response = self.client.post("/api/v3/access/login", json={"code": "wrong-code"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "ACCESS_CODE_INVALID")
        self.assertNotIn("vtn_session", response.cookies)

    def test_hosted_mode_disables_the_legacy_arbitrary_image_proxy(self):
        self.client.post("/api/v3/access/login", json={"code": self.code})

        response = self.client.get(
            "/api/proxy-image", params={"url": "http://127.0.0.1:8767/api/health"}
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "LEGACY_API_DISABLED")

    def test_hosted_mode_serves_the_owned_parser_record_thumbnail(self):
        class ThumbnailMedia(FakePlatformMedia):
            def resolve(self, url):
                metadata = super().resolve(url)
                metadata["thumbnail_url"] = (
                    "http://i1.hdslb.com/bfs/archive/fixture-cover.jpg"
                )
                return metadata

        class ThumbnailFetcher:
            def fetch(self, _url):
                return b"fixture-cover-bytes", "image/jpeg"

        parser = ParserWorkflow(
            self.repo,
            ThumbnailMedia(),
            FakeTranscriber(),
            run_in_background=False,
            access_manager=self.access,
        )
        app = FastAPI()
        app.include_router(
            create_v3_router(
                self.repo,
                parser,
                thumbnail_fetcher=ThumbnailFetcher(),
                access_manager=self.access,
            )
        )
        install_access_middleware(app, self.access)
        client = TestClient(app)
        client.post("/api/v3/access/login", json={"code": self.code})
        task = client.post(
            "/api/v3/parser/tasks",
            json={"source_url": "https://www.bilibili.com/video/BV1TEST"},
        ).json()["task"]

        response = client.get(
            f"/api/v3/parser/records/{task['record_id']}/thumbnail"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"fixture-cover-bytes")
        self.assertEqual(response.headers["content-type"], "image/jpeg")

    def test_parser_quota_and_history_are_isolated_per_invite_code(self):
        self.client.post("/api/v3/access/login", json={"code": self.code})
        created = self.client.post(
            "/api/v3/parser/tasks",
            json={"source_url": "https://example.test/friend-a", "device_id": "spoofed"},
        ).json()["task"]
        self.assertEqual(created["state"], "completed")
        record_id = created["record_id"]
        status = self.client.get("/api/v3/access/status").json()["access"]
        self.assertEqual(status["remaining_transcription_seconds"], 1200)

        friend_b_code = self.access.create_grant(
            "朋友 B", transcription_seconds_limit=1800, note_generation_limit=5,
            max_video_seconds=1200,
        )["code"]
        friend_b = TestClient(self.client.app)
        friend_b.post("/api/v3/access/login", json={"code": friend_b_code})
        self.assertEqual(friend_b.get("/api/v3/parser/records").json()["items"], [])
        self.assertEqual(
            friend_b.get(f"/api/v3/parser/records/{record_id}").status_code, 404
        )
        self.assertEqual(
            friend_b.get(f"/api/v3/parser/tasks/{created['id']}").status_code, 404
        )

    def test_video_over_remaining_quota_fails_before_transcription(self):
        limited_code = self.access.create_grant(
            "额度不足", transcription_seconds_limit=500, note_generation_limit=1,
            max_video_seconds=1200,
        )["code"]
        limited = TestClient(self.client.app)
        limited.post("/api/v3/access/login", json={"code": limited_code})
        task = limited.post(
            "/api/v3/parser/tasks", json={"source_url": "https://example.test/long"}
        ).json()["task"]
        self.assertEqual(task["state"], "failed")
        self.assertEqual(task["error_code"], "TRANSCRIPTION_QUOTA_EXCEEDED")
        self.assertEqual(
            limited.get("/api/v3/access/status").json()["access"]["remaining_transcription_seconds"],
            500,
        )

    def test_paid_call_pause_blocks_media_before_any_external_resolution(self):
        class UnexpectedMedia(FakePlatformMedia):
            def __init__(self):
                super().__init__()
                self.resolve_calls = 0

            def resolve(self, url):
                self.resolve_calls += 1
                raise AssertionError("付费调用暂停时不应访问视频平台")

        paused_access = AccessManager(
            self.repo,
            "test-session-secret",
            secure_cookie=False,
            paid_calls_enabled=False,
        )
        media = UnexpectedMedia()
        parser = ParserWorkflow(
            self.repo,
            media,
            FakeTranscriber(),
            run_in_background=False,
            access_manager=paused_access,
        )
        app = FastAPI()
        app.include_router(
            create_v3_router(self.repo, parser, access_manager=paused_access)
        )
        install_access_middleware(app, paused_access)
        client = TestClient(app)
        client.post("/api/v3/access/login", json={"code": self.code})

        task = client.post(
            "/api/v3/parser/tasks",
            json={"source_url": "https://www.bilibili.com/video/BV1TEST"},
        ).json()["task"]

        self.assertEqual(task["state"], "failed")
        self.assertEqual(task["error_code"], "PAID_CALLS_PAUSED")
        self.assertEqual(media.resolve_calls, 0)

    def test_local_parser_can_run_while_paid_note_generation_stays_paused(self):
        split_access = AccessManager(
            self.repo,
            "test-session-secret",
            secure_cookie=False,
            paid_calls_enabled=False,
            parser_calls_enabled=True,
        )
        parser = ParserWorkflow(
            self.repo,
            FakePlatformMedia(),
            FakeTranscriber(),
            run_in_background=False,
            access_manager=split_access,
        )
        notes = NoteWorkflow(
            self.repo,
            FakeLLM(),
            run_in_background=False,
            access_manager=split_access,
        )
        app = FastAPI()
        app.include_router(
            create_v3_router(
                self.repo,
                parser,
                notes,
                access_manager=split_access,
            )
        )
        install_access_middleware(app, split_access)
        client = TestClient(app)
        client.post("/api/v3/access/login", json={"code": self.code})

        parser_task = client.post(
            "/api/v3/parser/tasks",
            json={"source_url": "https://www.bilibili.com/video/BV1TEST"},
        ).json()["task"]
        note_response = client.post(
            "/api/v3/note-tasks",
            json={
                "source": {
                    "type": "paste",
                    "name": "测试逐字稿",
                    "transcript": "此处不会调用真实 LLM",
                }
            },
        )

        self.assertEqual(parser_task["state"], "completed")
        self.assertEqual(note_response.status_code, 429)
        self.assertEqual(
            note_response.json()["error"]["code"],
            "PAID_CALLS_PAUSED",
        )

    def test_note_quota_and_saved_notes_are_isolated_per_invite_code(self):
        self.client.post("/api/v3/access/login", json={"code": self.code})
        task = self.client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "spoofed",
                "source": {"type": "paste", "name": "输入", "transcript": "内测逐字稿"},
            },
        ).json()["task"]
        completed = self.client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={"type": "start_generation"},
        ).json()["task"]
        note_id = completed["note_id"]
        self.assertEqual(
            self.client.get("/api/v3/access/status").json()["access"]["remaining_note_generations"],
            4,
        )

        friend_b_code = self.access.create_grant(
            "朋友 B", transcription_seconds_limit=1800, note_generation_limit=5,
            max_video_seconds=1200,
        )["code"]
        friend_b = TestClient(self.client.app)
        friend_b.post("/api/v3/access/login", json={"code": friend_b_code})
        self.assertEqual(friend_b.get("/api/v3/note-tasks").json()["items"], [])
        self.assertEqual(friend_b.get("/api/v3/notes").json()["items"], [])
        self.assertEqual(friend_b.get(f"/api/v3/note-tasks/{task['id']}").status_code, 404)
        self.assertEqual(friend_b.get(f"/api/v3/notes/{note_id}").status_code, 404)

    def test_invalid_note_input_is_rejected_before_reserving_quota(self):
        self.client.post("/api/v3/access/login", json={"code": self.code})

        response = self.client.post(
            "/api/v3/note-tasks",
            json={
                "source": {"type": "paste", "name": "空输入", "transcript": "   "},
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "EMPTY_TRANSCRIPT")
        status = self.client.get("/api/v3/access/status").json()["access"]
        self.assertEqual(status["remaining_note_generations"], 5)

    def test_unknown_note_source_is_rejected_before_reserving_quota(self):
        self.client.post("/api/v3/access/login", json={"code": self.code})

        response = self.client.post(
            "/api/v3/note-tasks",
            json={
                "source": {
                    "type": "remote_url", "name": "未知来源", "transcript": "逐字稿",
                },
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "INVALID_NOTE_SOURCE")
        status = self.client.get("/api/v3/access/status").json()["access"]
        self.assertEqual(status["remaining_note_generations"], 5)

    def test_failed_transcription_releases_reserved_quota(self):
        class FailedTranscriber(FakeTranscriber):
            def transcribe(self, _audio_path):
                raise DomainError(
                    "TRANSCRIPTION_UPLOAD_TIMEOUT", "测试转录失败", retryable=True
                )

        parser = ParserWorkflow(
            self.repo, FakePlatformMedia(), FailedTranscriber(),
            run_in_background=False, access_manager=self.access,
        )
        app = FastAPI()
        app.include_router(create_v3_router(self.repo, parser, access_manager=self.access))
        install_access_middleware(app, self.access)
        client = TestClient(app)
        client.post("/api/v3/access/login", json={"code": self.code})

        task = client.post(
            "/api/v3/parser/tasks", json={"source_url": "https://example.test/failure"}
        ).json()["task"]

        self.assertEqual(task["state"], "failed")
        status = client.get("/api/v3/access/status").json()["access"]
        self.assertEqual(status["remaining_transcription_seconds"], 1800)

    def test_failed_note_analysis_releases_reserved_quota(self):
        class FailedAnalysisLLM(FakeLLM):
            def analyze(self, _transcript, _request_text):
                raise DomainError("LLM_TIMEOUT", "测试预读失败", retryable=True)

        notes = NoteWorkflow(
            self.repo, FailedAnalysisLLM(), run_in_background=False,
            access_manager=self.access,
        )
        app = FastAPI()
        app.include_router(create_v3_router(
            self.repo,
            ParserWorkflow(
                self.repo, FakePlatformMedia(), FakeTranscriber(),
                run_in_background=False, access_manager=self.access,
            ),
            notes,
            NoteDocument(self.repo, FailedAnalysisLLM()),
            Exporter(self.repo),
            access_manager=self.access,
        ))
        install_access_middleware(app, self.access)
        client = TestClient(app)
        client.post("/api/v3/access/login", json={"code": self.code})

        task = client.post(
            "/api/v3/note-tasks",
            json={"source": {"type": "paste", "name": "输入", "transcript": "逐字稿"}},
        ).json()["task"]

        self.assertEqual(task["state"], "analysis_failed")
        status = client.get("/api/v3/access/status").json()["access"]
        self.assertEqual(status["remaining_note_generations"], 5)

    def test_failed_outline_regeneration_releases_reserved_quota(self):
        class FailedOutlineRevisionLLM(FakeLLM):
            def generate_outline(self, task, feedback=""):
                if feedback:
                    raise DomainError("LLM_TIMEOUT", "测试大纲重拟失败", retryable=True)
                return super().generate_outline(task, feedback)

        llm = FailedOutlineRevisionLLM()
        notes = NoteWorkflow(
            self.repo, llm, run_in_background=False, access_manager=self.access
        )
        app = FastAPI()
        app.include_router(create_v3_router(
            self.repo,
            ParserWorkflow(
                self.repo, FakePlatformMedia(), FakeTranscriber(),
                run_in_background=False, access_manager=self.access,
            ),
            notes,
            NoteDocument(self.repo, llm),
            Exporter(self.repo),
            access_manager=self.access,
        ))
        install_access_middleware(app, self.access)
        client = TestClient(app)
        client.post("/api/v3/access/login", json={"code": self.code})
        task = client.post(
            "/api/v3/note-tasks",
            json={"source": {"type": "paste", "name": "输入", "transcript": "逐字稿"}},
        ).json()["task"]
        client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={"type": "save_settings", "settings": {"method": "outline"}},
        )
        client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={"type": "start_generation"},
        )

        response = client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={"type": "regenerate_outline", "feedback": "补充要求"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["task"]["state"], "generation_failed")
        status = client.get("/api/v3/access/status").json()["access"]
        self.assertEqual(status["remaining_note_generations"], 5)


if __name__ == "__main__":
    unittest.main()
