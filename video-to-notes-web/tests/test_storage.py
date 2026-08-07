import tempfile
import unittest
from pathlib import Path

from vtn.storage.sqlite import SQLiteRepository


class SQLiteRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "test.sqlite3"
        self.repo = SQLiteRepository(self.db_path)
        self.repo.migrate()

    def tearDown(self):
        self.repo.close()
        self.tempdir.cleanup()

    def test_migration_is_idempotent_and_creates_domain_tables(self):
        self.repo.migrate()
        tables = self.repo.table_names()
        self.assertTrue(
            {
                "parser_tasks",
                "parser_records",
                "note_tasks",
                "note_chapters",
                "notes",
                "note_versions",
                "chapter_candidates",
                "parse_note_links",
                "workflow_events",
            }.issubset(tables)
        )

    def test_workflow_event_sequence_is_monotonic_and_resumable(self):
        first = self.repo.append_event("parser", "task-1", "state", {"state": "resolving"})
        second = self.repo.append_event("parser", "task-1", "progress", {"stage": "metadata"})
        self.assertEqual((first.seq, second.seq), (1, 2))
        resumed = self.repo.list_events("parser", "task-1", after_seq=1)
        self.assertEqual([event.seq for event in resumed], [2])
        self.assertEqual(resumed[0].payload["stage"], "metadata")

    def test_deleting_parser_record_only_removes_link_not_note(self):
        self.repo.create_parser_record(
            {
                "id": "record-1",
                "source_url": "https://example.test/video",
                "platform": "other",
                "title": "Source",
                "creator": "",
                "description": "",
                "duration_seconds": 1,
                "thumbnail_url": "",
                "transcript_text": "parser copy",
            }
        )
        self.repo.create_note_task(
            {
                "id": "note-task-1",
                "device_id": "device",
                "state": "complete",
                "source_type": "parser",
                "source_name": "Source",
                "source_snapshot": {"parser_record_id": "record-1"},
                "basis_transcript": "note copy",
                "request_text": "",
                "proposed_title": "Note",
            }
        )
        self.repo.create_note(
            {
                "id": "note-1",
                "task_id": "note-task-1",
                "title": "Note",
                "current_markdown": "# Note",
                "integrity": {"status": "ok"},
                "source_snapshot": {"parser_record_id": "record-1"},
                "basis_transcript": "note copy",
            }
        )
        self.repo.link_parser_note("record-1", "note-task-1")

        self.repo.delete_parser_record("record-1")

        self.assertIsNone(self.repo.get_parser_record("record-1"))
        self.assertEqual(self.repo.get_note("note-1")["basis_transcript"], "note copy")

    def test_startup_recovery_marks_interrupted_tasks_without_losing_completed_chapters(self):
        self.repo.create_parser_task(
            {
                "id": "parser-running", "device_id": "device",
                "source_url": "https://example.test", "state": "transcribing",
            }
        )
        self.repo.create_note_task(
            {
                "id": "note-running", "device_id": "device", "state": "generating_chapters",
                "source_type": "paste", "source_name": "source",
                "source_snapshot": {}, "basis_transcript": "text",
                "request_text": "", "proposed_title": "Note",
            }
        )
        self.repo.replace_note_chapters(
            "note-running",
            [{"id": "c1", "title": "完成"}, {"id": "c2", "title": "进行中"}],
        )
        chapter_ids = [chapter["id"] for chapter in self.repo.list_note_chapters("note-running")]
        self.repo.update_note_chapter(chapter_ids[0], status="complete", content_md="kept")
        self.repo.update_note_chapter(chapter_ids[1], status="running")
        self.repo.recover_interrupted_tasks()
        self.assertEqual(self.repo.get_parser_task("parser-running")["state"], "failed")
        self.assertEqual(self.repo.get_note_task("note-running")["state"], "chapter_failed")
        chapters = self.repo.list_note_chapters("note-running")
        self.assertEqual(chapters[0]["content_md"], "kept")
        self.assertEqual(chapters[1]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
