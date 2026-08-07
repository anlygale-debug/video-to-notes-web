import tempfile
import threading
import time
import unittest
import re
from pathlib import Path

from vtn.adapters.llm import FakeLLM
from vtn.documents.notes import NoteDocument
from vtn.domain.errors import DomainError
from vtn.exports.exporter import Exporter
from vtn.storage.sqlite import SQLiteRepository


class NoteDocumentExporterTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = SQLiteRepository(Path(self.tempdir.name) / "test.sqlite3")
        self.repo.migrate()
        self.repo.create_note_task(
            {
                "id": "task", "device_id": "browser", "state": "complete",
                "source_type": "paste", "source_name": "逐字稿",
                "source_snapshot": {"type": "paste", "name": "逐字稿"},
                "basis_transcript": "生成依据全文", "request_text": "",
                "proposed_title": "测试笔记",
            }
        )
        self.repo.create_note(
            {
                "id": "note", "task_id": "task", "title": "测试笔记",
                "current_markdown": "# 测试笔记\n\n## 第一章\n\n初始内容\n",
                "basis_transcript": "生成依据全文",
                "source_snapshot": {"type": "paste", "name": "逐字稿"},
                "integrity": {"status": "ok"},
            }
        )
        self.document = NoteDocument(self.repo, FakeLLM())

    def tearDown(self):
        self.repo.close()
        self.tempdir.cleanup()

    def test_optimistic_save_rejects_stale_version(self):
        saved = self.document.save("note", 1, "新标题", "# 新标题\n\n修改内容")
        self.assertEqual(saved["version"], 2)
        with self.assertRaises(DomainError) as context:
            self.document.save("note", 1, "旧标题", "旧内容")
        self.assertEqual(context.exception.code, "NOTE_VERSION_CONFLICT")

    def test_restore_keeps_ai_initial_immutable(self):
        self.document.save("note", 1, "新标题", "# 新标题\n\n修改内容")
        restored = self.document.restore_ai_initial("note", 2)
        self.assertIn("初始内容", restored["current_markdown"])
        self.assertEqual(self.repo.count_note_versions("note", "ai_initial"), 1)
        self.assertEqual(self.repo.count_note_versions("note", "before_restore"), 1)

    def test_export_uses_latest_version_and_optional_basis(self):
        self.document.save("note", 1, "新标题", "# 新标题\n\n## 第一章\n\n最新内容")
        exporter = Exporter(self.repo)
        markdown = exporter.markdown("note", include_transcript=True, include_source=True)
        self.assertIn("最新内容", markdown.content)
        self.assertIn("生成依据逐字稿", markdown.content)
        self.assertIn("来源类型：paste", markdown.content)
        self.assertNotIn("初始内容", markdown.content)
        self.assertEqual(
            re.findall(r"(?m)^##\s+(.+)$", markdown.content),
            ["第一章"],
        )

    def test_accepting_regenerated_chapter_preserves_document_heading_contract(self):
        class WrapperHeavyLLM(FakeLLM):
            def generate_chapter(self, task, chapter, previous_summary):
                return {
                    "content": (
                        "### 核心摘要\n\n不应写入成品的候选摘要。\n\n"
                        "### 正文\n\n候选正文已经更新。"
                    ),
                    "summary": "候选正文摘要",
                }

        document = NoteDocument(self.repo, WrapperHeavyLLM())
        candidate = document.regenerate_chapter("note", "第一章")
        saved = document.decide_candidate("note", candidate["id"], "accept", 1)

        self.assertEqual(saved["current_markdown"].count("## 第一章"), 1)
        self.assertIn("候选正文已经更新。", saved["current_markdown"])
        self.assertNotRegex(saved["current_markdown"], r"(?m)^#{1,6}\s+(核心摘要|正文)$")

    def test_document_llm_operations_share_the_global_heavy_task_lock(self):
        llm_entered = threading.Event()
        heavy_task_lock = threading.Lock()

        class ObservedLLM(FakeLLM):
            def check_integrity(self, task, markdown):
                llm_entered.set()
                return {"status": "ok"}

        document = NoteDocument(
            self.repo, ObservedLLM(), heavy_task_lock=heavy_task_lock
        )
        heavy_task_lock.acquire()
        worker = threading.Thread(target=document.recheck_integrity, args=("note",))
        worker.start()
        time.sleep(0.05)
        self.assertFalse(llm_entered.is_set())

        heavy_task_lock.release()
        worker.join(1)
        self.assertTrue(llm_entered.is_set())
        self.assertFalse(worker.is_alive())


if __name__ == "__main__":
    unittest.main()
