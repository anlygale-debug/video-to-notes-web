import re

from vtn.domain.errors import DomainError


MODULE_LABELS = {
    "summary": "核心摘要",
    "concepts": "关键概念",
    "actions": "实践提炼",
    "review_questions": "复习问题",
}
FORBIDDEN_SECTION_TITLES = set(MODULE_LABELS.values()) | {"正文"}


def _heading(line):
    match = re.match(r"^\s*(#{1,6})\s+(.+?)\s*$", line)
    if not match:
        return None
    title = re.sub(r"[*_`~]", "", match.group(2)).strip().rstrip("：:")
    return len(match.group(1)), title


def _mermaid_node_label(value):
    value = value.strip().strip(";")
    match = re.search(r'[\[\{\("]([^\]\}\)"]+)[\]\}\)"]', value)
    if match:
        return match.group(1).strip()
    return re.sub(r"^[A-Za-z0-9_-]+$", "", value).strip()


def _replace_mermaid(markdown):
    def fallback(match):
        relations = []
        for line in match.group(1).splitlines():
            if "-->" not in line:
                continue
            labels = [_mermaid_node_label(part) for part in line.split("-->")]
            labels = [label for label in labels if label]
            if len(labels) >= 2:
                relations.append(f"- {' → '.join(labels)}")
        if not relations:
            relations = ["- 核心概念 → 成因理解 → 行动练习"]
        return (
            "> 关系图已转换为结构化文字，避免不稳定图表影响阅读。\n\n"
            + "\n".join(relations)
        )

    return re.sub(
        r"```\s*mermaid\s*\n(.*?)```",
        fallback,
        markdown,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _strip_forbidden_sections(markdown, *, chapter_title=None):
    lines = (markdown or "").replace("\r\n", "\n").split("\n")
    output = []
    skipped_level = None
    for line in lines:
        heading = _heading(line)
        if skipped_level is not None:
            if not heading or heading[0] > skipped_level:
                continue
            skipped_level = None
        if heading:
            level, title = heading
            if title in MODULE_LABELS.values():
                skipped_level = level
                continue
            if title == "正文" or (chapter_title and title == chapter_title):
                continue
            output.append(f"{'#' * max(level, 3)} {title}")
            continue
        output.append(line)
    cleaned = _replace_mermaid("\n".join(output))
    cleaned = re.sub(r"(?m)^\s*([-*_])(?:\s*\1){2,}\s*$", "", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _normalize_supplement(module_id, markdown):
    """Accept a harmless matching wrapper while still rejecting model-owned sections."""
    lines = (markdown or "").replace("\r\n", "\n").split("\n")
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        heading = _heading(line)
        if heading and heading[1] == MODULE_LABELS[module_id]:
            lines.pop(index)
        break
    return _strip_forbidden_sections("\n".join(lines))


class NoteMarkdownComposer:
    """Owns the complete Markdown structure; model output is content only."""

    def __init__(self, title, chapter_titles, selected_modules):
        self.title = title.strip() or "未命名笔记"
        self.chapter_titles = [title.strip() for title in chapter_titles if title.strip()]
        self.selected_modules = [module for module in selected_modules if module in MODULE_LABELS]
        if not self.chapter_titles:
            raise DomainError("NOTE_STRUCTURE_INVALID", "笔记至少需要一个正文篇章")
        if len(set(self.chapter_titles)) != len(self.chapter_titles):
            raise DomainError("NOTE_STRUCTURE_INVALID", "笔记篇章标题不能重复")

    def normalize_chapter(self, title, raw_markdown):
        content = _strip_forbidden_sections(raw_markdown, chapter_title=title)
        if not content:
            raise DomainError("NOTE_STRUCTURE_INVALID", f"篇章《{title}》没有可用正文")
        return content

    def compose(self, chapter_drafts, supplements=None, *, require_supplements=False):
        supplements = supplements or {}
        if [draft["title"] for draft in chapter_drafts] != self.chapter_titles:
            raise DomainError("NOTE_STRUCTURE_INVALID", "生成篇章与已确认大纲不一致")

        if require_supplements:
            missing = [
                MODULE_LABELS[module_id]
                for module_id in self.selected_modules
                if not _normalize_supplement(module_id, supplements.get(module_id, ""))
            ]
            if missing:
                raise DomainError(
                    "NOTE_MODULES_INCOMPLETE", f"附加模块未完整生成：{'、'.join(missing)}"
                )

        parts = [f"# {self.title}"]
        summary = _normalize_supplement("summary", supplements.get("summary", ""))
        if "summary" in self.selected_modules and summary:
            quoted = "\n".join(f"> {line}" if line else ">" for line in summary.splitlines())
            parts.append(f"> **核心摘要**\n>\n{quoted}")

        for draft in chapter_drafts:
            content = self.normalize_chapter(draft["title"], draft.get("content", ""))
            parts.append(f"## {draft['title']}\n\n{content}")

        for module_id in self.selected_modules:
            if module_id == "summary":
                continue
            content = _normalize_supplement(module_id, supplements.get(module_id, ""))
            if content:
                parts.append(f"**复习增强｜{MODULE_LABELS[module_id]}**\n\n{content}")

        markdown = "\n\n".join(parts)
        markdown = markdown.strip() + "\n"
        self.validate(markdown)
        return markdown

    def validate(self, markdown):
        h1 = [match.group(1).strip() for match in re.finditer(r"(?m)^#\s+(.+)$", markdown)]
        h2 = [match.group(1).strip() for match in re.finditer(r"(?m)^##\s+(.+)$", markdown)]
        forbidden = [
            match.group(1).strip().rstrip("：:")
            for match in re.finditer(r"(?m)^#{1,6}\s+(.+)$", markdown)
            if re.sub(r"[*_`~]", "", match.group(1)).strip().rstrip("：:")
            in FORBIDDEN_SECTION_TITLES
        ]
        if h1 != [self.title] or h2 != self.chapter_titles or forbidden:
            raise DomainError("NOTE_STRUCTURE_INVALID", "成品笔记结构未通过篇章一致性检查")
