import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path

from vtn.domain.models import WorkflowEvent, utc_now


class SQLiteRepository:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._connection:
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA busy_timeout = 5000")

    def close(self):
        with self._lock:
            self._connection.close()

    def _fetchone(self, sql, parameters=()):
        with self._lock:
            return self._connection.execute(sql, parameters).fetchone()

    def _fetchall(self, sql, parameters=()):
        with self._lock:
            return self._connection.execute(sql, parameters).fetchall()

    @contextmanager
    def transaction(self):
        with self._lock:
            with self._connection:
                yield self._connection

    def migrate(self):
        schema_path = Path(__file__).with_name("schema.sql")
        with self._lock, self._connection:
            self._connection.executescript(schema_path.read_text(encoding="utf-8"))
            parser_task_columns = {
                row["name"]
                for row in self._connection.execute("PRAGMA table_info(parser_tasks)")
            }
            if "error_retryable" not in parser_task_columns:
                self._connection.execute(
                    "ALTER TABLE parser_tasks ADD COLUMN error_retryable INTEGER"
                )
            parser_record_columns = {
                row["name"]
                for row in self._connection.execute("PRAGMA table_info(parser_records)")
            }
            if "access_id" not in parser_record_columns:
                self._connection.execute(
                    "ALTER TABLE parser_records ADD COLUMN access_id TEXT "
                    "REFERENCES access_grants(id) ON DELETE SET NULL"
                )
            note_task_columns = {
                row["name"]
                for row in self._connection.execute("PRAGMA table_info(note_tasks)")
            }
            if "llm_profile_id" not in note_task_columns:
                self._connection.execute(
                    "ALTER TABLE note_tasks ADD COLUMN llm_profile_id TEXT"
                )
            self._connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES(1, ?)",
                (utc_now(),),
            )
            self._connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES(2, ?)",
                (utc_now(),),
            )
            self._connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES(3, ?)",
                (utc_now(),),
            )
            self._connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES(4, ?)",
                (utc_now(),),
            )
            self._connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES(5, ?)",
                (utc_now(),),
            )

    def table_names(self):
        rows = self._fetchall("SELECT name FROM sqlite_master WHERE type='table'")
        return {row["name"] for row in rows}

    def append_event(self, workflow_type, task_id, event_type, payload):
        now = utc_now()
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM workflow_events "
                "WHERE workflow_type=? AND task_id=?",
                (workflow_type, task_id),
            ).fetchone()
            seq = row["next_seq"]
            connection.execute(
                "INSERT INTO workflow_events(workflow_type,task_id,seq,event_type,payload_json,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (workflow_type, task_id, seq, event_type, json.dumps(payload, ensure_ascii=False), now),
            )
        return WorkflowEvent(workflow_type, task_id, seq, event_type, payload, now)

    def list_events(self, workflow_type, task_id, after_seq=0):
        rows = self._fetchall(
            "SELECT * FROM workflow_events WHERE workflow_type=? AND task_id=? AND seq>? ORDER BY seq",
            (workflow_type, task_id, after_seq),
        )
        return [
            WorkflowEvent(
                row["workflow_type"],
                row["task_id"],
                row["seq"],
                row["event_type"],
                json.loads(row["payload_json"]),
                row["created_at"],
            )
            for row in rows
        ]

    def create_parser_record(self, record):
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO parser_records(
                   id,access_id,source_url,platform,title,creator,description,duration_seconds,
                   thumbnail_url,transcript_text,transcript_format_version,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    record["id"], record.get("access_id"), record["source_url"],
                    record["platform"], record["title"],
                    record.get("creator", ""), record.get("description", ""),
                    record.get("duration_seconds", 0), record.get("thumbnail_url", ""),
                    record["transcript_text"], record.get("transcript_format_version", 1),
                    now, now,
                ),
            )
        return self.get_parser_record(record["id"])

    def create_parser_task(self, task):
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO parser_tasks(
                   id,device_id,source_url,platform_hint,state,progress_json,
                   retry_count,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    task["id"], task["device_id"], task["source_url"],
                    task.get("platform_hint", "other"), task.get("state", "created"),
                    json.dumps(task.get("progress", {}), ensure_ascii=False),
                    task.get("retry_count", 0), now, now,
                ),
            )
        return self.get_parser_task(task["id"])

    def get_parser_task(self, task_id):
        row = self._fetchone(
            "SELECT * FROM parser_tasks WHERE id=?", (task_id,)
        )
        task = self._decode_row(row, ["progress_json"])
        if task and task.get("error_retryable") is not None:
            task["error_retryable"] = bool(task["error_retryable"])
        return task

    def update_parser_task(self, task_id, **changes):
        mapping = {
            "state": "state", "error_code": "error_code", "error_message": "error_message",
            "error_retryable": "error_retryable",
            "retry_count": "retry_count", "record_id": "record_id",
            "progress": "progress_json",
        }
        assignments, values = [], []
        for key, value in changes.items():
            if key not in mapping:
                continue
            assignments.append(f"{mapping[key]}=?")
            values.append(json.dumps(value, ensure_ascii=False) if key == "progress" else value)
        if not assignments:
            return self.get_parser_task(task_id)
        assignments.append("updated_at=?")
        values.extend([utc_now(), task_id])
        with self.transaction() as connection:
            connection.execute(
                f"UPDATE parser_tasks SET {', '.join(assignments)} WHERE id=?", values
            )
        return self.get_parser_task(task_id)

    def get_parser_record(self, record_id, access_id=None):
        sql = "SELECT * FROM parser_records WHERE id=?"
        parameters = [record_id]
        if access_id is not None:
            sql += " AND access_id=?"
            parameters.append(access_id)
        row = self._fetchone(sql, parameters)
        return dict(row) if row else None

    def list_parser_records(self, limit=30, cursor=None, access_id=None):
        cursor_clause = ""
        parameters = []
        clauses = []
        if access_id is not None:
            clauses.append("r.access_id=?")
            parameters.append(access_id)
        if cursor:
            clauses.append("(r.created_at < ? OR (r.created_at = ? AND r.id < ?))")
            parameters.extend([cursor[0], cursor[0], cursor[1]])
        cursor_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._fetchall(
            f"""SELECT r.*,
               (SELECT l.note_task_id FROM parse_note_links l
                JOIN note_tasks t ON t.id=l.note_task_id
                WHERE l.parse_record_id=r.id ORDER BY t.created_at DESC LIMIT 1) AS note_task_id,
               (SELECT t.note_id FROM parse_note_links l
                JOIN note_tasks t ON t.id=l.note_task_id
                WHERE l.parse_record_id=r.id AND t.note_id IS NOT NULL
                ORDER BY t.created_at DESC LIMIT 1) AS note_id
               FROM parser_records r
               {cursor_clause}
               ORDER BY r.created_at DESC, r.id DESC LIMIT ?""",
            (*parameters, limit),
        )
        return [dict(row) for row in rows]

    def delete_parser_record(self, record_id):
        with self.transaction() as connection:
            connection.execute("DELETE FROM parser_records WHERE id=?", (record_id,))

    def create_note_task(self, task):
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO note_tasks(
                   id,device_id,state,source_type,source_name,source_snapshot_json,
                   basis_transcript,transcript_revision,request_text,llm_profile_id,
                   proposed_title,progress_json,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    task["id"], task["device_id"], task["state"], task["source_type"],
                    task.get("source_name", ""),
                    json.dumps(task.get("source_snapshot", {}), ensure_ascii=False),
                    task["basis_transcript"], task.get("transcript_revision", 1),
                    task.get("request_text", ""), task.get("llm_profile_id"),
                    task.get("proposed_title", ""),
                    json.dumps(task.get("progress", {}), ensure_ascii=False), now, now,
                ),
            )
        return self.get_note_task(task["id"])

    def get_note_task(self, task_id):
        row = self._fetchone(
            "SELECT * FROM note_tasks WHERE id=?", (task_id,)
        )
        return self._decode_row(row, ["source_snapshot_json", "recommendation_json",
                                      "final_settings_json", "outline_json", "progress_json"])

    def update_note_task(self, task_id, **changes):
        mapping = {
            "state": "state", "basis_transcript": "basis_transcript",
            "transcript_revision": "transcript_revision", "request_text": "request_text",
            "proposed_title": "proposed_title", "recommendation": "recommendation_json",
            "recommendation_revision": "recommendation_revision",
            "final_settings": "final_settings_json", "outline": "outline_json",
            "outline_feedback": "outline_feedback", "progress": "progress_json",
            "error_code": "error_code", "error_message": "error_message", "note_id": "note_id",
        }
        json_keys = {"recommendation", "final_settings", "outline", "progress"}
        assignments, values = [], []
        for key, value in changes.items():
            if key not in mapping:
                continue
            assignments.append(f"{mapping[key]}=?")
            values.append(
                json.dumps(value, ensure_ascii=False) if key in json_keys and value is not None else value
            )
        if not assignments:
            return self.get_note_task(task_id)
        assignments.append("updated_at=?")
        values.extend([utc_now(), task_id])
        with self.transaction() as connection:
            connection.execute(f"UPDATE note_tasks SET {', '.join(assignments)} WHERE id=?", values)
        return self.get_note_task(task_id)

    def list_note_tasks(self, device_id=None, limit=30, cursor=None):
        cursor_clause = ""
        cursor_parameters = []
        if cursor:
            cursor_clause = "(created_at < ? OR (created_at = ? AND id < ?))"
            cursor_parameters.extend([cursor[0], cursor[0], cursor[1]])
        if device_id:
            where_clause = "WHERE device_id=?"
            if cursor_clause:
                where_clause += f" AND {cursor_clause}"
            rows = self._fetchall(
                f"SELECT * FROM note_tasks {where_clause} "
                "ORDER BY created_at DESC,id DESC LIMIT ?",
                (device_id, *cursor_parameters, limit),
            )
        else:
            where_clause = f"WHERE {cursor_clause}" if cursor_clause else ""
            rows = self._fetchall(
                f"SELECT * FROM note_tasks {where_clause} "
                "ORDER BY created_at DESC,id DESC LIMIT ?",
                (*cursor_parameters, limit),
            )
        return [
            self._decode_row(row, ["source_snapshot_json", "recommendation_json",
                                   "final_settings_json", "outline_json", "progress_json"])
            for row in rows
        ]

    def replace_note_chapters(self, task_id, chapters):
        with self.transaction() as connection:
            connection.execute("DELETE FROM note_chapters WHERE task_id=?", (task_id,))
            for position, chapter in enumerate(chapters, start=1):
                chapter_id = f"{task_id}:{chapter.get('id') or position}"
                connection.execute(
                    """INSERT INTO note_chapters(
                       id,task_id,position,title,status,content_md,context_summary,attempt_count
                    ) VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        chapter_id, task_id, position,
                        chapter["title"], "waiting", "", "", 0,
                    ),
                )

    def list_note_chapters(self, task_id):
        rows = self._fetchall(
            "SELECT * FROM note_chapters WHERE task_id=? ORDER BY position", (task_id,)
        )
        return [dict(row) for row in rows]

    def update_note_chapter(self, chapter_id, **changes):
        allowed = {"status", "content_md", "context_summary", "attempt_count"}
        items = [(key, value) for key, value in changes.items() if key in allowed]
        if not items:
            return
        with self.transaction() as connection:
            connection.execute(
                f"UPDATE note_chapters SET {', '.join(f'{key}=?' for key, _ in items)} WHERE id=?",
                [value for _, value in items] + [chapter_id],
            )

    def create_note(self, note):
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO notes(
                   id,task_id,title,current_markdown,version,integrity_json,
                   source_snapshot_json,basis_transcript,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    note["id"], note["task_id"], note["title"], note["current_markdown"],
                    note.get("version", 1),
                    json.dumps(note.get("integrity", {"status": "ok"}), ensure_ascii=False),
                    json.dumps(note.get("source_snapshot", {}), ensure_ascii=False),
                    note["basis_transcript"], now, now,
                ),
            )
            connection.execute(
                "UPDATE note_tasks SET note_id=?, state='complete', updated_at=? WHERE id=?",
                (note["id"], now, note["task_id"]),
            )
            connection.execute(
                "INSERT INTO note_versions(id,note_id,kind,title,markdown,created_at) VALUES(?,?,?,?,?,?)",
                (str(uuid.uuid4()), note["id"], "ai_initial", note["title"],
                 note["current_markdown"], now),
            )
        return self.get_note(note["id"])

    def get_note(self, note_id):
        row = self._fetchone("SELECT * FROM notes WHERE id=?", (note_id,))
        return self._decode_row(row, ["integrity_json", "source_snapshot_json"])

    def update_note_integrity(self, note_id, integrity):
        with self.transaction() as connection:
            connection.execute(
                "UPDATE notes SET integrity_json=? WHERE id=?",
                (json.dumps(integrity, ensure_ascii=False), note_id),
            )
        return self.get_note(note_id)

    def list_notes(self, limit=30, cursor=None, access_id=None):
        parameters = []
        clauses = []
        if access_id is not None:
            clauses.append("t.device_id=?")
            parameters.append(access_id)
        if cursor:
            clauses.append("(n.created_at < ? OR (n.created_at = ? AND n.id < ?))")
            parameters.extend([cursor[0], cursor[0], cursor[1]])
        cursor_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._fetchall(
            f"""SELECT n.*, t.source_type, t.source_name, t.state AS task_state,
                      l.parse_record_id AS parser_record_id
               FROM notes n JOIN note_tasks t ON t.id=n.task_id
               LEFT JOIN parse_note_links l ON l.note_task_id=t.id
               {cursor_clause}
               ORDER BY n.created_at DESC,n.id DESC LIMIT ?""",
            (*parameters, limit),
        )
        return [
            self._decode_row(row, ["integrity_json", "source_snapshot_json"]) for row in rows
        ]

    def count_note_versions(self, note_id, kind=None):
        if kind:
            row = self._fetchone(
                "SELECT COUNT(*) AS count FROM note_versions WHERE note_id=? AND kind=?",
                (note_id, kind),
            )
        else:
            row = self._fetchone(
                "SELECT COUNT(*) AS count FROM note_versions WHERE note_id=?", (note_id,)
            )
        return row["count"]

    def get_note_version(self, note_id, kind):
        row = self._fetchone(
            "SELECT * FROM note_versions WHERE note_id=? AND kind=? ORDER BY created_at LIMIT 1",
            (note_id, kind),
        )
        return dict(row) if row else None

    def add_note_version(self, note_id, kind, title, markdown):
        version_id = str(uuid.uuid4())
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO note_versions(id,note_id,kind,title,markdown,created_at) VALUES(?,?,?,?,?,?)",
                (version_id, note_id, kind, title, markdown, utc_now()),
            )
        return version_id

    def save_note(self, note_id, expected_version, title, markdown):
        now = utc_now()
        with self.transaction() as connection:
            cursor = connection.execute(
                """UPDATE notes SET title=?,current_markdown=?,version=version+1,updated_at=?
                   WHERE id=? AND version=?""",
                (title, markdown, now, note_id, expected_version),
            )
            if cursor.rowcount != 1:
                return None
            connection.execute(
                "UPDATE note_tasks SET proposed_title=?,updated_at=? "
                "WHERE id=(SELECT task_id FROM notes WHERE id=?)",
                (title, now, note_id),
            )
        return self.get_note(note_id)

    def create_candidate(self, candidate):
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO chapter_candidates(
                   id,note_id,chapter_id,current_chapter_markdown,candidate_markdown,status,created_at
                ) VALUES(?,?,?,?,?,'pending',?)""",
                (
                    candidate["id"], candidate["note_id"], candidate["chapter_id"],
                    candidate["current_chapter_markdown"], candidate["candidate_markdown"],
                    utc_now(),
                ),
            )
        return self.get_candidate(candidate["id"])

    def get_candidate(self, candidate_id):
        row = self._fetchone(
            "SELECT * FROM chapter_candidates WHERE id=?", (candidate_id,)
        )
        return dict(row) if row else None

    def decide_candidate(self, candidate_id, status):
        with self.transaction() as connection:
            connection.execute(
                "UPDATE chapter_candidates SET status=? WHERE id=?", (status, candidate_id)
            )
        return self.get_candidate(candidate_id)

    def delete_note(self, note_id):
        note = self.get_note(note_id)
        if not note:
            return False
        with self.transaction() as connection:
            connection.execute("DELETE FROM note_tasks WHERE id=?", (note["task_id"],))
        return True

    def delete_note_task(self, task_id):
        with self.transaction() as connection:
            connection.execute(
                "DELETE FROM workflow_events WHERE workflow_type='note' AND task_id=?",
                (task_id,),
            )
            cursor = connection.execute("DELETE FROM note_tasks WHERE id=?", (task_id,))
        return cursor.rowcount == 1

    def recover_interrupted_tasks(self):
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                """UPDATE parser_tasks
                   SET state='failed',error_code='PROCESS_INTERRUPTED',
                       error_message='本地服务曾中断，请重试解析',error_retryable=1,
                       progress_json='{}',updated_at=?
                   WHERE state IN ('resolving','transcribing','retrying')""",
                (now,),
            )
            connection.execute(
                """UPDATE note_tasks
                   SET state='generation_failed',error_code='PROCESS_INTERRUPTED',
                       error_message='本地服务曾中断，可以重新继续当前阶段',updated_at=?
                   WHERE state IN ('analyzing','generating_direct')""",
                (now,),
            )
            running_tasks = connection.execute(
                "SELECT DISTINCT task_id FROM note_chapters WHERE status='running'"
            ).fetchall()
            connection.execute("UPDATE note_chapters SET status='failed' WHERE status='running'")
            for row in running_tasks:
                connection.execute(
                    """UPDATE note_tasks SET state='chapter_failed',
                       error_code='PROCESS_INTERRUPTED',
                       error_message='章节生成曾中断，已完成章节仍然保留',updated_at=?
                       WHERE id=?""",
                    (now, row["task_id"]),
                )

    def parser_record_exists_for_url(self, source_url):
        row = self._fetchone(
            "SELECT id FROM parser_records WHERE source_url=? LIMIT 1", (source_url,)
        )
        return row["id"] if row else None

    def link_parser_note(self, record_id, task_id):
        with self.transaction() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO parse_note_links(parse_record_id,note_task_id) VALUES(?,?)",
                (record_id, task_id),
            )

    @staticmethod
    def _decode_row(row, json_fields):
        if not row:
            return None
        result = dict(row)
        for field in json_fields:
            value = result.get(field)
            if value:
                result[field.removesuffix("_json")] = json.loads(value)
        return result
