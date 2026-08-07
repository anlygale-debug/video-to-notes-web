import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from vtn.adapters.llm import FakeLLM
from vtn.adapters.media import FakePlatformMedia
from vtn.adapters.transcription import FakeTranscriber
from vtn.documents.notes import NoteDocument
from vtn.exports.exporter import Exporter
from vtn.storage.sqlite import SQLiteRepository
from vtn.web.api import create_v3_router
from vtn.workflows.notes import NoteWorkflow
from vtn.workflows.parser import ParserWorkflow


class NoteHttpTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = SQLiteRepository(Path(self.tempdir.name) / "test.sqlite3")
        self.repo.migrate()
        llm = FakeLLM()
        parser = ParserWorkflow(
            self.repo, FakePlatformMedia(), FakeTranscriber(), run_in_background=False
        )
        notes = NoteWorkflow(self.repo, llm, run_in_background=False)
        app = FastAPI()
        app.include_router(
            create_v3_router(self.repo, parser, notes, NoteDocument(self.repo, llm), Exporter(self.repo))
        )
        self.client = TestClient(app)

    def tearDown(self):
        self.repo.close()
        self.tempdir.cleanup()

    def test_direct_note_flow_and_export_contract(self):
        created = self.client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {"type": "paste", "name": "输入", "transcript": "亲密关系逐字稿"},
                "request_text": "保留行动建议",
            },
        )
        self.assertEqual(created.status_code, 202)
        task = created.json()["task"]
        generated = self.client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={"type": "start_generation"},
        ).json()["task"]
        self.assertEqual(generated["state"], "complete")
        note = self.client.get(f"/api/v3/notes/{generated['note_id']}").json()["note"]
        exported = self.client.get(
            f"/api/v3/notes/{note['id']}/export?format=md&content=note_transcript&source=include"
        )
        self.assertIn("生成依据逐字稿", exported.text)
        self.assertIn("亲密关系逐字稿", exported.text)

    def test_abandoning_unfinished_task_removes_it_from_recovery(self):
        created = self.client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "待放弃输入",
                    "transcript": "这份逐字稿会在推荐阶段被主动放弃。",
                },
            },
        ).json()["task"]

        response = self.client.delete(f"/api/v3/note-tasks/{created['id']}")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            self.client.get(f"/api/v3/note-tasks/{created['id']}").status_code,
            404,
        )
        task_ids = {
            task["id"]
            for task in self.client.get(
                "/api/v3/note-tasks", params={"device_id": "browser"}
            ).json()["items"]
        }
        self.assertNotIn(created["id"], task_ids)
        self.assertEqual(self.repo.list_events("note", created["id"]), [])

    def test_abandoning_running_generation_discards_late_llm_result(self):
        generation_entered = threading.Event()
        release_generation = threading.Event()

        class BlockingDirectLLM(FakeLLM):
            def generate_direct(self, task):
                generation_entered.set()
                release_generation.wait(2)
                return super().generate_direct(task)

        llm = BlockingDirectLLM()
        parser = ParserWorkflow(
            self.repo, FakePlatformMedia(), FakeTranscriber(), run_in_background=False
        )
        notes = NoteWorkflow(self.repo, llm, run_in_background=True)
        app = FastAPI()
        app.include_router(
            create_v3_router(
                self.repo, parser, notes, NoteDocument(self.repo, llm), Exporter(self.repo)
            )
        )
        client = TestClient(app)
        task = client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "运行中放弃",
                    "transcript": "这份逐字稿会在模型正在生成时被主动放弃。",
                },
            },
        ).json()["task"]
        for _ in range(100):
            task = client.get(f"/api/v3/note-tasks/{task['id']}").json()["task"]
            if task["state"] == "recommendation_ready":
                break
            threading.Event().wait(0.01)
        else:
            self.fail("笔记分析未进入 recommendation_ready")

        client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={"type": "start_generation"},
        )
        self.assertTrue(generation_entered.wait(1), "模型生成没有开始")

        deleted = client.delete(f"/api/v3/note-tasks/{task['id']}")
        release_generation.set()
        threading.Event().wait(0.05)

        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(client.get(f"/api/v3/note-tasks/{task['id']}").status_code, 404)
        self.assertEqual(self.repo.list_notes(limit=10), [])
        self.assertEqual(self.repo.list_events("note", task["id"]), [])

    def test_retry_integrity_check_updates_only_the_saved_check_result(self):
        class RetryIntegrityLLM(FakeLLM):
            def __init__(self):
                super().__init__()
                self.check_count = 0

            def check_integrity(self, task, markdown):
                self.check_count += 1
                if self.check_count == 1:
                    return {
                        "status": "check_unavailable",
                        "check_failed": True,
                        "error_code": "LLM_REQUEST_FAILED",
                        "error_message": "AI 请求失败：测试连接超时",
                        "retryable": True,
                    }
                return {"status": "ok"}

        llm = RetryIntegrityLLM()
        parser = ParserWorkflow(
            self.repo, FakePlatformMedia(), FakeTranscriber(), run_in_background=False
        )
        notes = NoteWorkflow(self.repo, llm, run_in_background=False)
        app = FastAPI()
        app.include_router(
            create_v3_router(
                self.repo, parser, notes, NoteDocument(self.repo, llm), Exporter(self.repo)
            )
        )
        client = TestClient(app)
        task = client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "输入",
                    "transcript": "用于重新检查的逐字稿",
                },
            },
        ).json()["task"]
        completed = client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={"type": "start_generation"},
        ).json()["task"]
        before = client.get(f"/api/v3/notes/{completed['note_id']}").json()["note"]

        response = client.post(f"/api/v3/notes/{before['id']}/integrity-check")
        after = response.json()["note"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(before["integrity"]["status"], "check_unavailable")
        self.assertEqual(after["integrity"], {"status": "ok"})
        self.assertEqual(after["title"], before["title"])
        self.assertEqual(after["current_markdown"], before["current_markdown"])
        self.assertEqual(after["version"], before["version"])
        self.assertEqual(llm.check_count, 2)

    def test_generation_command_leaves_recommendation_state_before_returning(self):
        llm = FakeLLM()
        notes = NoteWorkflow(self.repo, llm, run_in_background=True)
        parser = ParserWorkflow(
            self.repo, FakePlatformMedia(), FakeTranscriber(), run_in_background=False
        )
        app = FastAPI()
        app.include_router(
            create_v3_router(
                self.repo, parser, notes, NoteDocument(self.repo, llm), Exporter(self.repo)
            )
        )
        client = TestClient(app)
        created = client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "输入",
                    "transcript": "用于验证生成启动状态的逐字稿。",
                },
            },
        ).json()["task"]
        for _ in range(100):
            ready = client.get(f"/api/v3/note-tasks/{created['id']}").json()["task"]
            if ready["state"] == "recommendation_ready":
                break
            threading.Event().wait(0.01)
        else:
            self.fail("笔记分析未进入 recommendation_ready")

        with patch("vtn.workflows.notes.threading.Thread") as deferred_thread:
            started = client.post(
                f"/api/v3/note-tasks/{created['id']}/commands",
                json={"type": "start_generation"},
            ).json()["task"]
        self.assertEqual(started["state"], "generating_direct")
        deferred_thread.assert_called_once()

    def test_confirming_outline_returns_real_chapter_progress_before_worker_runs(self):
        llm = FakeLLM()
        notes = NoteWorkflow(self.repo, llm, run_in_background=True)
        parser = ParserWorkflow(
            self.repo, FakePlatformMedia(), FakeTranscriber(), run_in_background=False
        )
        app = FastAPI()
        app.include_router(
            create_v3_router(
                self.repo, parser, notes, NoteDocument(self.repo, llm), Exporter(self.repo)
            )
        )
        client = TestClient(app)
        task = client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "输入",
                    "transcript": "逐章生成进度测试逐字稿。",
                },
            },
        ).json()["task"]
        for _ in range(100):
            task = client.get(f"/api/v3/note-tasks/{task['id']}").json()["task"]
            if task["state"] == "recommendation_ready":
                break
            threading.Event().wait(0.01)
        client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={
                "type": "save_settings",
                "settings": {
                    "structure": "problem_solution",
                    "detail": "complete",
                    "method": "outline",
                    "modules": ["summary"],
                },
            },
        )
        client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={"type": "start_generation"},
        )
        for _ in range(100):
            task = client.get(f"/api/v3/note-tasks/{task['id']}").json()["task"]
            if task["state"] == "outline_ready":
                break
            threading.Event().wait(0.01)
        else:
            self.fail("大纲未进入 outline_ready")

        with patch("vtn.workflows.notes.threading.Thread") as deferred_thread:
            confirmed = client.post(
                f"/api/v3/note-tasks/{task['id']}/commands",
                json={"type": "confirm_outline"},
            ).json()["task"]

        self.assertEqual(confirmed["state"], "generating_chapters")
        self.assertEqual(
            [chapter["status"] for chapter in confirmed["chapters"]],
            ["waiting", "waiting", "waiting"],
        )
        deferred_thread.assert_called_once()

    def test_analysis_returns_a_small_semantic_recommendation_instead_of_a_quiz(self):
        class QuizShapedLLM(FakeLLM):
            def analyze(self, transcript, request_text):
                return {
                    "title": "控制欲的成因",
                    "reason": "逐字稿包含多个心理机制。",
                    "structure": {
                        "question": "控制欲有哪些原因？",
                        "options": [
                            {"id": "trauma", "label": "童年创伤"},
                            {"id": "all", "label": "以上都是"},
                        ],
                        "recommended_id": "all",
                    },
                    "detail": {"recommended_id": "complete"},
                    "method": {"recommended_id": "outline"},
                    "modules": {
                        "recommended_ids": [
                            "summary", "concepts", "actions", "cases",
                            "review_questions", "glossary", "quotes", "mermaid",
                        ]
                    },
                }

        llm = QuizShapedLLM()
        notes = NoteWorkflow(self.repo, llm, run_in_background=False)
        parser = ParserWorkflow(
            self.repo, FakePlatformMedia(), FakeTranscriber(), run_in_background=False
        )
        app = FastAPI()
        app.include_router(
            create_v3_router(
                self.repo, parser, notes, NoteDocument(self.repo, llm), Exporter(self.repo)
            )
        )
        client = TestClient(app)
        task = client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "输入",
                    "transcript": "逐字稿从童年经历讲到成年关系，再给出觉察练习。",
                },
            },
        ).json()["task"]

        recommendation = task["recommendation"]
        self.assertEqual(
            recommendation["structure"]["question"], "这份笔记最适合怎样组织？"
        )
        self.assertEqual(
            [option["id"] for option in recommendation["structure"]["options"]],
            ["source_flow", "thematic", "problem_solution"],
        )
        self.assertEqual(recommendation["structure"]["recommended_id"], "source_flow")
        self.assertEqual(recommendation["method"]["recommended_id"], "outline")
        self.assertEqual(
            recommendation["modules"]["recommended_ids"],
            ["summary", "concepts", "actions"],
        )

    def test_body_only_recommendation_stays_empty_in_automatic_generation_plan(self):
        class BodyOnlyLLM(FakeLLM):
            def analyze(self, transcript, request_text):
                recommendation = super().analyze(transcript, request_text)
                recommendation["modules"] = {
                    "recommended_ids": [],
                    "reasons": {},
                }
                return recommendation

        llm = BodyOnlyLLM()
        notes = NoteWorkflow(self.repo, llm, run_in_background=False)
        parser = ParserWorkflow(
            self.repo, FakePlatformMedia(), FakeTranscriber(), run_in_background=False
        )
        app = FastAPI()
        app.include_router(
            create_v3_router(
                self.repo, parser, notes, NoteDocument(self.repo, llm), Exporter(self.repo)
            )
        )
        client = TestClient(app)
        task = client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "输入",
                    "transcript": "这份逐字稿本身已经有完整的章节与重点。",
                },
            },
        ).json()["task"]

        self.assertEqual(task["recommendation"]["modules"]["recommended_ids"], [])
        generated = client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={"type": "start_generation"},
        ).json()["task"]
        self.assertEqual(generated["final_settings"]["modules"], [])

    def test_automatic_and_custom_generation_share_one_complete_generation_plan(self):
        automatic = self.client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "自动输入",
                    "transcript": "这是一份按原因、方法和练习展开的逐字稿。",
                },
            },
        ).json()["task"]
        automatic = self.client.post(
            f"/api/v3/note-tasks/{automatic['id']}/commands",
            json={"type": "start_generation"},
        ).json()["task"]
        automatic_plan = automatic["final_settings"]
        self.assertEqual(automatic_plan["structure"]["id"], "problem_solution")
        self.assertEqual(automatic_plan["detail"]["id"], "complete")
        self.assertEqual(automatic_plan["method"], "direct")
        self.assertLessEqual(len(automatic_plan["modules"]), 3)

        custom = self.client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "自定义输入",
                    "transcript": "这是一份需要重新按主题归类的逐字稿。",
                },
            },
        ).json()["task"]
        saved = self.client.post(
            f"/api/v3/note-tasks/{custom['id']}/commands",
            json={
                "type": "save_settings",
                "settings": {
                    "structure": "thematic",
                    "detail": "key",
                    "method": "direct",
                    "modules": ["summary", "actions"],
                    "additional_request": "多保留失败案例，并明确给出下一步行动。",
                },
            },
        ).json()["task"]
        custom_plan = saved["final_settings"]
        self.assertEqual(custom_plan["structure"]["id"], "thematic")
        self.assertEqual(custom_plan["structure"]["label"], "按主题分类")
        self.assertEqual(custom_plan["detail"]["id"], "key")
        self.assertEqual(
            [module["id"] for module in custom_plan["modules"]],
            ["summary", "actions"],
        )
        self.assertEqual(
            custom_plan["additional_request"],
            "多保留失败案例，并明确给出下一步行动。",
        )
        completed = self.client.post(
            f"/api/v3/note-tasks/{custom['id']}/commands",
            json={"type": "start_generation"},
        ).json()["task"]
        self.assertEqual(completed["state"], "complete")
        self.assertEqual(completed["final_settings"], custom_plan)

    def test_user_can_return_from_outline_and_change_settings_without_reanalysis(self):
        task = self.client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "输入",
                    "transcript": "先解释问题，再分析原因，最后给出行动方法。",
                },
            },
        ).json()["task"]
        self.client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={
                "type": "save_settings",
                "settings": {
                    "structure": "problem_solution",
                    "detail": "complete",
                    "method": "outline",
                    "modules": ["summary", "actions"],
                },
            },
        )
        outlined = self.client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={"type": "start_generation"},
        ).json()["task"]
        self.assertEqual(outlined["state"], "outline_ready")

        changed = self.client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={
                "type": "save_settings",
                "settings": {
                    "structure": "thematic",
                    "detail": "key",
                    "method": "direct",
                    "modules": ["concepts"],
                    "additional_request": "改成主题式复习笔记。",
                },
            },
        )
        self.assertEqual(changed.status_code, 200)
        changed_task = changed.json()["task"]
        self.assertEqual(changed_task["state"], "recommendation_ready")
        self.assertIsNone(changed_task.get("outline"))
        self.assertEqual(changed_task["recommendation_revision"], task["recommendation_revision"])

        completed = self.client.post(
            f"/api/v3/note-tasks/{task['id']}/commands",
            json={"type": "start_generation"},
        ).json()["task"]
        self.assertEqual(completed["state"], "complete")

    def test_opening_a_legacy_task_upgrades_its_old_quiz_recommendation(self):
        task = self.client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "旧任务",
                    "transcript": "旧任务逐字稿保持不变。",
                },
            },
        ).json()["task"]
        self.repo.update_note_task(
            task["id"],
            recommendation={
                "title": "旧推荐",
                "reason": "旧版推荐",
                "structure": {
                    "question": "内容中的原因是什么？",
                    "options": [
                        {"id": "adaptive-1", "label": "原因 A"},
                        {"id": "adaptive-2", "label": "以上都是"},
                    ],
                    "recommended_id": "adaptive-2",
                },
                "detail": {"recommended_id": "complete"},
                "method": {"recommended_id": "direct"},
                "modules": {
                    "recommended_ids": [
                        "summary", "concepts", "actions", "cases",
                        "review_questions", "glossary", "quotes", "mermaid",
                    ]
                },
            },
        )

        opened = self.client.get(f"/api/v3/note-tasks/{task['id']}").json()["task"]

        self.assertEqual(opened["basis_transcript"], "旧任务逐字稿保持不变。")
        self.assertEqual(
            opened["recommendation"]["structure"]["question"],
            "这份笔记最适合怎样组织？",
        )
        self.assertEqual(
            [option["id"] for option in opened["recommendation"]["structure"]["options"]],
            ["source_flow", "thematic", "problem_solution"],
        )
        self.assertLessEqual(
            len(opened["recommendation"]["modules"]["recommended_ids"]), 3
        )

    def test_completed_note_can_start_a_new_analysis_without_overwriting_the_original(self):
        original_task = self.client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "原始逐字稿",
                    "transcript": "需要重新组织并展开说明的完整逐字稿。",
                },
                "request_text": "先生成一份简洁笔记",
            },
        ).json()["task"]
        original_task = self.client.post(
            f"/api/v3/note-tasks/{original_task['id']}/commands",
            json={"type": "start_generation"},
        ).json()["task"]
        original_note = self.client.get(
            f"/api/v3/notes/{original_task['note_id']}"
        ).json()["note"]

        restarted = self.client.post(
            "/api/v3/note-tasks",
            json={
                "device_id": "browser",
                "source": {"type": "note", "note_id": original_note["id"]},
                "request_text": "重新生成得更详细，增加概念解释、案例和行动步骤。",
            },
        )

        self.assertEqual(restarted.status_code, 202)
        restarted_task = restarted.json()["task"]
        self.assertNotEqual(restarted_task["id"], original_task["id"])
        self.assertIsNone(restarted_task["note_id"])
        self.assertEqual(restarted_task["basis_transcript"], original_note["basis_transcript"])
        self.assertEqual(
            restarted_task["request_text"],
            "重新生成得更详细，增加概念解释、案例和行动步骤。",
        )
        self.assertEqual(
            restarted_task["source_snapshot"]["regenerated_from_note_id"],
            original_note["id"],
        )

        regenerated_task = self.client.post(
            f"/api/v3/note-tasks/{restarted_task['id']}/commands",
            json={"type": "start_generation"},
        ).json()["task"]
        self.assertNotEqual(regenerated_task["note_id"], original_note["id"])
        preserved_original = self.client.get(
            f"/api/v3/notes/{original_note['id']}"
        ).json()["note"]
        self.assertEqual(preserved_original["current_markdown"], original_note["current_markdown"])
        self.assertEqual(preserved_original["version"], original_note["version"])

    def test_browser_history_migration_imports_legacy_notes_idempotently(self):
        payload = {
            "transcripts": [
                {
                    "id": "legacy-parser",
                    "url": "https://www.bilibili.com/video/BV1LEGACY",
                    "title": "旧视频",
                    "platform": "bilibili",
                    "transcript": "旧解析逐字稿",
                }
            ],
            "notes": [
                {
                    "id": "legacy-note",
                    "title": "旧版成品笔记",
                    "platform": "bilibili",
                    "url": "https://www.bilibili.com/video/BV1LEGACY",
                    "notes": "# 旧版成品笔记\n\n## 核心内容\n\n迁移后仍可阅读。",
                }
            ],
        }

        first = self.client.post("/api/v3/migrations/browser-history", json=payload)
        second = self.client.post("/api/v3/migrations/browser-history", json=payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["imported"], {"parser_records": 1, "notes": 1})
        self.assertEqual(second.json()["imported"], {"parser_records": 0, "notes": 0})
        notes = self.client.get("/api/v3/notes").json()["items"]
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["title"], "旧版成品笔记")
        self.assertEqual(notes[0]["parser_record_id"], "legacy-parser")

    def test_history_routes_return_stable_cursor_pages(self):
        payload = {"transcripts": [], "notes": []}
        for index in range(3):
            url = f"https://example.com/video-{index}"
            payload["transcripts"].append(
                {"id": f"record-{index}", "url": url, "title": f"解析 {index}", "transcript": "逐字稿"}
            )
            payload["notes"].append(
                {"id": f"note-{index}", "url": url, "title": f"笔记 {index}", "notes": f"# 笔记 {index}"}
            )
        self.client.post("/api/v3/migrations/browser-history", json=payload)

        parser_first = self.client.get("/api/v3/parser/records?limit=2").json()
        parser_second = self.client.get(
            "/api/v3/parser/records", params={"limit": 2, "cursor": parser_first["next_cursor"]}
        ).json()
        notes_first = self.client.get("/api/v3/notes?limit=2").json()
        notes_second = self.client.get(
            "/api/v3/notes", params={"limit": 2, "cursor": notes_first["next_cursor"]}
        ).json()

        self.assertEqual(len(parser_first["items"]), 2)
        self.assertEqual(len(parser_second["items"]), 1)
        self.assertIsNotNone(parser_first["next_cursor"])
        self.assertEqual(len(notes_first["items"]), 2)
        self.assertEqual(len(notes_second["items"]), 1)
        self.assertIsNotNone(notes_first["next_cursor"])

    def test_note_task_history_uses_cursor_and_rejects_invalid_cursors(self):
        for index in range(3):
            response = self.client.post(
                "/api/v3/note-tasks",
                json={
                    "device_id": "browser",
                    "source": {
                        "type": "paste",
                        "name": f"输入 {index}",
                        "transcript": f"逐字稿 {index}",
                    },
                },
            )
            self.assertEqual(response.status_code, 202)

        first = self.client.get(
            "/api/v3/note-tasks", params={"device_id": "browser", "limit": 2}
        ).json()
        second = self.client.get(
            "/api/v3/note-tasks",
            params={"device_id": "browser", "limit": 2, "cursor": first["next_cursor"]},
        ).json()

        self.assertEqual(len(first["items"]), 2)
        self.assertIsNotNone(first["next_cursor"])
        self.assertEqual(len(second["items"]), 1)
        for path in ("/api/v3/parser/records", "/api/v3/note-tasks", "/api/v3/notes"):
            response = self.client.get(path, params={"cursor": "not-a-valid-cursor"})
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["error"]["code"], "INVALID_CURSOR")


if __name__ == "__main__":
    unittest.main()
