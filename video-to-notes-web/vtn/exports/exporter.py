import re
from dataclasses import dataclass

from vtn.domain.errors import DomainError


@dataclass(frozen=True)
class ExportResult:
    filename: str
    content: str
    media_type: str


class Exporter:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def safe_filename(title):
        safe = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "", title).strip()
        return (safe or "笔记")[:80]

    def markdown(self, note_id, *, include_transcript=False, include_source=False):
        note = self.repository.get_note(note_id)
        if not note:
            raise DomainError("NOTE_NOT_FOUND", "笔记不存在")
        content = note["current_markdown"].rstrip() + "\n"
        source = note["source_snapshot"]
        if include_source:
            content += (
                "\n---\n\n**附录｜来源信息**\n\n"
                f"- 来源类型：{source.get('type', 'unknown')}\n"
                f"- 来源名称：{source.get('title') or source.get('name') or '未命名'}\n"
            )
            if source.get("creator"):
                content += f"- 作者：{source['creator']}\n"
            if source.get("platform"):
                content += f"- 平台：{source['platform']}\n"
            if source.get("source_url"):
                content += f"- 原链接：{source['source_url']}\n"
        if include_transcript:
            content += (
                "\n---\n\n**附录｜生成依据逐字稿**\n\n"
                + note["basis_transcript"].rstrip()
                + "\n"
            )
        return ExportResult(
            f"{self.safe_filename(note['title'])}.md", content, "text/markdown; charset=utf-8"
        )
