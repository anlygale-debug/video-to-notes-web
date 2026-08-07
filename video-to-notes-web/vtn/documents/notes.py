import re
import uuid
from contextlib import nullcontext

from vtn.documents.composer import NoteMarkdownComposer
from vtn.domain.errors import DomainError


class NoteDocument:
    def __init__(self, repository, llm, *, heavy_task_lock=None):
        self.repository = repository
        self.llm = llm
        self.heavy_task_lock = heavy_task_lock

    def _heavy_task(self):
        return self.heavy_task_lock or nullcontext()

    def _llm_for_task(self, task):
        bind = getattr(self.llm, "for_profile", None)
        return bind(task.get("llm_profile_id")) if bind else self.llm

    def get(self, note_id):
        note = self.repository.get_note(note_id)
        if not note:
            raise DomainError("NOTE_NOT_FOUND", "笔记不存在")
        return note

    def save(self, note_id, expected_version, title, markdown, *, checkpoint=False):
        current = self.get(note_id)
        if checkpoint:
            self.repository.add_note_version(
                note_id, "user_checkpoint", current["title"], current["current_markdown"]
            )
        saved = self.repository.save_note(note_id, expected_version, title.strip(), markdown)
        if not saved:
            raise DomainError(
                "NOTE_VERSION_CONFLICT",
                "笔记已在其他位置更新，请重新载入后再保存",
                retryable=True,
                details={"current_version": self.get(note_id)["version"]},
            )
        return saved

    def restore_ai_initial(self, note_id, expected_version):
        current = self.get(note_id)
        if current["version"] != expected_version:
            raise DomainError("NOTE_VERSION_CONFLICT", "笔记版本已变化", retryable=True)
        initial = self.repository.get_note_version(note_id, "ai_initial")
        if not initial:
            raise DomainError("AI_INITIAL_NOT_FOUND", "找不到 AI 初始版本")
        self.repository.add_note_version(
            note_id, "before_restore", current["title"], current["current_markdown"]
        )
        return self.save(
            note_id, expected_version, initial["title"], initial["markdown"], checkpoint=False
        )

    def recheck_integrity(self, note_id):
        note = self.get(note_id)
        task = self.repository.get_note_task(note["task_id"])
        if not task:
            raise DomainError("NOTE_TASK_NOT_FOUND", "笔记任务不存在")
        with self._heavy_task():
            integrity = self._llm_for_task(task).check_integrity(
                task, note["current_markdown"]
            )
        if integrity.get("check_failed") and integrity.get("status") == "ok":
            integrity = {**integrity, "status": "check_unavailable"}
        return self.repository.update_note_integrity(note_id, integrity)

    def regenerate_chapter(self, note_id, chapter_id):
        note = self.get(note_id)
        pattern = re.compile(
            rf"(^##\s+{re.escape(chapter_id)}.*?)(?=^##\s+|\Z)", re.M | re.S
        )
        match = pattern.search(note["current_markdown"])
        if not match:
            raise DomainError("CHAPTER_NOT_FOUND", "无法定位该章节")
        current_chapter = match.group(1).strip()
        task = self.repository.get_note_task(note["task_id"])
        with self._heavy_task():
            generated = self._llm_for_task(task).generate_chapter(
                task, {"id": chapter_id, "title": chapter_id}, ""
            )
        module_ids = [
            module.get("id") for module in (task.get("final_settings") or {}).get("modules", [])
        ]
        composer = NoteMarkdownComposer(note["title"], [chapter_id], module_ids)
        candidate_body = composer.normalize_chapter(chapter_id, generated.get("content", ""))
        return self.repository.create_candidate(
            {
                "id": str(uuid.uuid4()), "note_id": note_id, "chapter_id": chapter_id,
                "current_chapter_markdown": current_chapter,
                "candidate_markdown": f"## {chapter_id}\n\n{candidate_body}",
            }
        )

    def decide_candidate(self, note_id, candidate_id, decision, expected_version):
        note = self.get(note_id)
        candidate = self.repository.get_candidate(candidate_id)
        if not candidate or candidate["note_id"] != note_id or candidate["status"] != "pending":
            raise DomainError("CANDIDATE_NOT_FOUND", "候选版本不存在")
        if decision == "reject":
            self.repository.decide_candidate(candidate_id, "rejected")
            return note
        if decision != "accept":
            raise DomainError("INVALID_CANDIDATE_DECISION", "请选择替换或保留")
        if note["version"] != expected_version:
            raise DomainError("NOTE_VERSION_CONFLICT", "笔记版本已变化", retryable=True)
        self.repository.add_note_version(
            note_id, "candidate_accept", note["title"], note["current_markdown"]
        )
        markdown = note["current_markdown"].replace(
            candidate["current_chapter_markdown"], candidate["candidate_markdown"], 1
        )
        saved = self.save(note_id, expected_version, note["title"], markdown)
        self.repository.decide_candidate(candidate_id, "accepted")
        return saved
