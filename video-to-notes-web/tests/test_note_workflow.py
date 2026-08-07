import tempfile
import unittest
import re
from itertools import combinations
from pathlib import Path
from unittest.mock import patch

from vtn.adapters.llm import FakeLLM
from vtn.domain.errors import DomainError
from vtn.storage.sqlite import SQLiteRepository
from vtn.workflows.notes import NoteWorkflow, normalize_generated_markdown


class NoteWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = SQLiteRepository(Path(self.tempdir.name) / "test.sqlite3")
        self.repo.migrate()
        self.llm = FakeLLM()
        self.workflow = NoteWorkflow(
            self.repo, self.llm, run_in_background=False
        )

    def tearDown(self):
        self.repo.close()
        self.tempdir.cleanup()

    def start_ready_task(self):
        return self.workflow.start_analysis(
            {
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "独立逐字稿",
                    "transcript": "关于亲密关系控制欲的完整逐字稿。",
                },
                "request_text": "用于复习，保留案例。",
            }
        )

    def test_transcript_change_expires_recommendation(self):
        task = self.start_ready_task()
        self.assertEqual(task["state"], "recommendation_ready")
        changed = self.workflow.command(
            task["id"], {"type": "update_transcript", "transcript": "修正后的逐字稿"}
        )
        self.assertEqual(changed["state"], "recommendation_stale")
        with self.assertRaises(DomainError):
            self.workflow.command(task["id"], {"type": "start_generation"})

    def test_direct_generation_creates_note_and_ai_initial_version(self):
        task = self.start_ready_task()
        self.workflow.command(
            task["id"],
            {"type": "save_settings", "settings": {"method": "direct", "detail": "complete"}},
        )
        completed = self.workflow.command(task["id"], {"type": "start_generation"})
        self.assertEqual(completed["state"], "complete")
        note = self.repo.get_note(completed["note_id"])
        self.assertIn("亲密关系", note["current_markdown"])
        self.assertEqual(self.repo.count_note_versions(note["id"], "ai_initial"), 1)

    def test_direct_note_uses_structured_chapters_instead_of_model_owned_headings(self):
        class StructuredDirectLLM(FakeLLM):
            def generate_direct(self, task):
                return {
                    "chapters": [
                        {
                            "title": "看见控制欲背后的问题",
                            "content_markdown": "### 正文\n\n问题篇章的独有正文。",
                        },
                        {
                            "title": "建立新的关系行动",
                            "content_markdown": (
                                "### 核心摘要\n\n越权摘要。\n\n"
                                "### 正文\n\n行动篇章的独有正文。"
                            ),
                        },
                    ],
                    "supplements": {
                        "summary": "### 核心摘要\n\n整份笔记的唯一摘要。"
                    },
                }

        workflow = NoteWorkflow(self.repo, StructuredDirectLLM(), run_in_background=False)
        task = workflow.start_analysis(
            {
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "直接生成逐字稿",
                    "transcript": "先解释问题，再给出行动。",
                },
            }
        )
        workflow.command(
            task["id"],
            {
                "type": "save_settings",
                "settings": {
                    "structure": "problem_solution",
                    "detail": "quick",
                    "method": "direct",
                    "modules": ["summary"],
                },
            },
        )
        completed = workflow.command(task["id"], {"type": "start_generation"})
        markdown = self.repo.get_note(completed["note_id"])["current_markdown"]

        self.assertEqual(
            [line.removeprefix("## ") for line in markdown.splitlines() if line.startswith("## ")],
            ["看见控制欲背后的问题", "建立新的关系行动"],
        )
        self.assertEqual(markdown.count("> **核心摘要**"), 1)
        self.assertNotRegex(markdown, r"(?m)^#{1,6}\s+(核心摘要|正文)$")
        self.assertIn("问题篇章的独有正文。", markdown)
        self.assertIn("行动篇章的独有正文。", markdown)

    def test_composed_note_converts_raw_mermaid_into_readable_text(self):
        class MermaidDirectLLM(FakeLLM):
            def generate_direct(self, task):
                return {
                    "chapters": [{
                        "title": "关系变化路径",
                        "content_markdown": (
                            "```mermaid\n"
                            "graph TD\n"
                            "A[分离创伤] --> B[控制冲动]\n"
                            "B --> C[边界练习]\n"
                            "```"
                        ),
                    }],
                    "supplements": {},
                }

        workflow = NoteWorkflow(self.repo, MermaidDirectLLM(), run_in_background=False)
        task = workflow.start_analysis({
            "device_id": "browser",
            "source": {
                "type": "paste",
                "name": "图表逐字稿",
                "transcript": "分离创伤可能引发控制冲动，可以通过边界练习调整。",
            },
        })
        workflow.command(
            task["id"],
            {"type": "save_settings", "settings": {"method": "direct", "modules": []}},
        )
        completed = workflow.command(task["id"], {"type": "start_generation"})
        markdown = self.repo.get_note(completed["note_id"])["current_markdown"]

        self.assertNotIn("mermaid", markdown.lower())
        self.assertNotIn("graph TD", markdown)
        self.assertIn("分离创伤 → 控制冲动", markdown)

    def test_duplicate_outline_titles_fail_before_outline_confirmation(self):
        class DuplicateOutlineLLM(FakeLLM):
            def generate_outline(self, task, feedback=""):
                return [
                    {"id": "chapter-01", "title": "重复篇章", "goal": "目标一"},
                    {"id": "chapter-02", "title": "重复篇章", "goal": "目标二"},
                ]

        workflow = NoteWorkflow(self.repo, DuplicateOutlineLLM(), run_in_background=False)
        task = workflow.start_analysis({
            "device_id": "browser",
            "source": {
                "type": "paste",
                "name": "重复大纲逐字稿",
                "transcript": "用于验证无效大纲不会进入确认页面。",
            },
        })
        workflow.command(
            task["id"],
            {"type": "save_settings", "settings": {"method": "outline", "modules": []}},
        )
        failed = workflow.command(task["id"], {"type": "start_generation"})

        self.assertEqual(failed["state"], "generation_failed")
        self.assertEqual(failed["error_code"], "NOTE_STRUCTURE_INVALID")
        self.assertIsNone(failed.get("outline"))

    def test_outline_confirmation_preserves_skill_style_subtopics(self):
        class DetailedOutlineLLM(FakeLLM):
            def generate_outline(self, task, feedback=""):
                return [
                    {
                        "id": "chapter-01",
                        "title": "先理解控制欲",
                        "goal": "建立问题框架",
                        "subtopics": ["关系中的典型表现", "控制背后的共同任务"],
                    },
                    {
                        "id": "chapter-02",
                        "title": "再拆解形成原因",
                        "goal": "解释三类根源",
                        "subtopics": ["分离创伤", "客体认同", "认知固化"],
                    },
                ]

        workflow = NoteWorkflow(self.repo, DetailedOutlineLLM(), run_in_background=False)
        task = workflow.start_analysis({
            "device_id": "browser",
            "source": {
                "type": "paste",
                "name": "详细大纲逐字稿",
                "transcript": "先描述控制欲，再解释三类形成原因。",
            },
        })
        workflow.command(
            task["id"],
            {"type": "save_settings", "settings": {"method": "outline", "modules": []}},
        )

        outlined = workflow.command(task["id"], {"type": "start_generation"})

        self.assertEqual(outlined["state"], "outline_ready")
        self.assertEqual(
            outlined["outline"][0]["subtopics"],
            ["关系中的典型表现", "控制背后的共同任务"],
        )
        self.assertEqual(
            outlined["outline"][1]["subtopics"],
            ["分离创伤", "客体认同", "认知固化"],
        )

    def test_long_outline_note_is_generated_in_connected_batches_with_cumulative_context(self):
        class ConnectedBatchLLM(FakeLLM):
            def generate_outline(self, task, feedback=""):
                return [
                    {
                        "id": f"chapter-{position:02d}",
                        "title": f"第 {position} 章",
                        "goal": f"只完成第 {position} 章的任务",
                        "subtopics": [f"主题 {position}.1", f"主题 {position}.2"],
                    }
                    for position in range(1, 8)
                ]

            def generate_chapter(self, task, chapter, previous_summary):
                raise DomainError(
                    "SINGLE_CHAPTER_CONTEXT_LOST",
                    "本测试不允许退回独立单章生成",
                    retryable=False,
                )

            def generate_chapter_batch(self, task, chapters, completed_context):
                if len(chapters) > 3:
                    raise DomainError(
                        "BATCH_TOO_LARGE",
                        "完整详解的长稿每批最多生成三章",
                        retryable=False,
                    )
                first_position = chapters[0]["position"]
                if first_position > 1:
                    required_title = f"第 {first_position - 1} 章"
                    if required_title not in completed_context:
                        raise DomainError(
                            "CUMULATIVE_CONTEXT_MISSING",
                            "后续批次没有收到全部已完成内容",
                            retryable=False,
                        )
                return [
                    {
                        "id": chapter["outline_id"],
                        "content": (
                            f"### {chapter['subtopics'][0]}\n\n"
                            f"{chapter['title']}的独有正文，并承接整篇大纲。"
                        ),
                        "summary": f"{chapter['title']}已经完成自己的内容范围",
                    }
                    for chapter in chapters
                ]

        workflow = NoteWorkflow(self.repo, ConnectedBatchLLM(), run_in_background=False)
        task = workflow.start_analysis({
            "device_id": "browser",
            "source": {
                "type": "paste",
                "name": "长篇课程逐字稿",
                "transcript": "这是需要保持前后连贯的长篇课程逐字稿。" * 1000,
            },
        })
        workflow.command(
            task["id"],
            {
                "type": "save_settings",
                "settings": {"method": "outline", "detail": "complete", "modules": []},
            },
        )
        outlined = workflow.command(task["id"], {"type": "start_generation"})

        completed = workflow.command(outlined["id"], {"type": "confirm_outline"})

        self.assertEqual(completed["state"], "complete")
        markdown = self.repo.get_note(completed["note_id"])["current_markdown"]
        for position in range(1, 8):
            self.assertEqual(markdown.count(f"## 第 {position} 章"), 1)
            self.assertIn(f"第 {position} 章的独有正文", markdown)

    def test_connected_batch_error_stops_immediately_and_retry_resumes_the_batch(self):
        class RetryableBatchLLM(FakeLLM):
            def __init__(self):
                super().__init__()
                self.should_fail = True

            def generate_outline(self, task, feedback=""):
                return [
                    {
                        "id": f"chapter-{position:02d}",
                        "title": f"连续章节 {position}",
                        "goal": f"完成范围 {position}",
                        "subtopics": [f"主题 {position}"],
                    }
                    for position in range(1, 6)
                ]

            def generate_chapter_batch(self, task, chapters, completed_context):
                if self.should_fail:
                    raise DomainError(
                        "LLM_TIMEOUT",
                        "AI 服务响应超时，已停止本批生成。",
                        retryable=True,
                    )
                return [
                    {
                        "id": chapter["outline_id"],
                        "content": f"### {chapter['subtopics'][0]}\n\n本章内容。",
                        "summary": f"{chapter['title']}已完成",
                    }
                    for chapter in chapters
                ]

        llm = RetryableBatchLLM()
        workflow = NoteWorkflow(self.repo, llm, run_in_background=False)
        task = workflow.start_analysis({
            "device_id": "browser",
            "source": {
                "type": "paste",
                "name": "批次失败逐字稿",
                "transcript": "用于验证失败立即停止。" * 2000,
            },
        })
        workflow.command(
            task["id"],
            {
                "type": "save_settings",
                "settings": {"method": "outline", "detail": "complete", "modules": []},
            },
        )
        outlined = workflow.command(task["id"], {"type": "start_generation"})

        failed = workflow.command(outlined["id"], {"type": "confirm_outline"})

        self.assertEqual(failed["state"], "chapter_failed")
        self.assertEqual(failed["error_code"], "LLM_TIMEOUT")
        self.assertEqual(
            [chapter["status"] for chapter in self.repo.list_note_chapters(task["id"])],
            ["failed", "waiting", "waiting", "waiting", "waiting"],
        )

        llm.should_fail = False
        completed = workflow.command(task["id"], {"type": "retry_failed_chapter"})

        self.assertEqual(completed["state"], "complete")
        self.assertEqual(
            [chapter["status"] for chapter in self.repo.list_note_chapters(task["id"])],
            ["complete", "complete", "complete", "complete", "complete"],
        )

    def test_long_direct_note_uses_hidden_outline_batches_without_extra_confirmation(self):
        class LongDirectBatchLLM(FakeLLM):
            def generate_direct(self, task):
                raise DomainError(
                    "DIRECT_OUTPUT_TOO_LARGE",
                    "长稿不应继续使用单次大输出",
                    retryable=False,
                )

            def generate_outline(self, task, feedback=""):
                return [
                    {
                        "id": f"chapter-{position:02d}",
                        "title": f"后台章节 {position}",
                        "goal": f"完成第 {position} 部分",
                        "subtopics": [f"主题 {position}"],
                    }
                    for position in range(1, 6)
                ]

            def generate_chapter_batch(self, task, chapters, completed_context):
                return [
                    {
                        "id": chapter["outline_id"],
                        "content": f"### {chapter['subtopics'][0]}\n\n连续生成内容。",
                        "summary": f"{chapter['title']}已完成",
                    }
                    for chapter in chapters
                ]

        workflow = NoteWorkflow(self.repo, LongDirectBatchLLM(), run_in_background=False)
        task = workflow.start_analysis({
            "device_id": "browser",
            "source": {
                "type": "paste",
                "name": "无需确认的长稿",
                "transcript": "这是一份需要后台连续分批的长篇逐字稿。" * 2000,
            },
        })
        workflow.command(
            task["id"],
            {
                "type": "save_settings",
                "settings": {"method": "direct", "detail": "complete", "modules": []},
            },
        )

        completed = workflow.command(task["id"], {"type": "start_generation"})

        self.assertEqual(completed["state"], "complete")
        self.assertIsNotNone(completed["note_id"])
        markdown = self.repo.get_note(completed["note_id"])["current_markdown"]
        self.assertEqual(markdown.count("## 后台章节"), 5)

    def test_failed_integrity_check_is_not_reported_as_ok(self):
        class CheckUnavailableLLM(FakeLLM):
            def check_integrity(self, task, markdown):
                return {"status": "ok", "check_failed": True}

        workflow = NoteWorkflow(self.repo, CheckUnavailableLLM(), run_in_background=False)
        task = workflow.start_analysis(
            {
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "检查状态逐字稿",
                    "transcript": "用于验证检查失败不会伪装成检查通过。",
                },
            }
        )
        completed = workflow.command(task["id"], {"type": "start_generation"})
        note = self.repo.get_note(completed["note_id"])

        self.assertEqual(note["integrity"]["status"], "check_unavailable")
        self.assertTrue(note["integrity"]["check_failed"])

    def test_selected_modules_cannot_silently_disappear(self):
        class MissingSupplementLLM(FakeLLM):
            def generate_supplements(self, task, body_markdown):
                return {}

        workflow = NoteWorkflow(self.repo, MissingSupplementLLM(), run_in_background=False)
        task = workflow.start_analysis(
            {
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "模块完整性逐字稿",
                    "transcript": "用于验证选中的模块不能静默丢失。",
                },
            }
        )
        workflow.command(
            task["id"],
            {
                "type": "save_settings",
                "settings": {
                    "method": "outline",
                    "modules": ["summary", "review_questions"],
                },
            },
        )
        outlined = workflow.command(task["id"], {"type": "start_generation"})
        failed = workflow.command(task["id"], {"type": "confirm_outline"})

        self.assertEqual(outlined["state"], "outline_ready")
        self.assertEqual(failed["state"], "generation_failed")
        self.assertEqual(failed["error_code"], "NOTE_MODULES_INCOMPLETE")

    def test_outline_failure_retains_completed_chapters_and_retries_failed_only(self):
        self.llm.fail_chapter_position = 2
        task = self.start_ready_task()
        self.workflow.command(
            task["id"],
            {"type": "save_settings", "settings": {"method": "outline", "detail": "complete"}},
        )
        outlined = self.workflow.command(task["id"], {"type": "start_generation"})
        self.assertEqual(outlined["state"], "outline_ready")
        failed = self.workflow.command(outlined["id"], {"type": "confirm_outline"})
        self.assertEqual(failed["state"], "chapter_failed")
        chapters = self.repo.list_note_chapters(task["id"])
        self.assertEqual([c["status"] for c in chapters], ["complete", "failed", "waiting"])
        self.llm.fail_chapter_position = None
        completed = self.workflow.command(task["id"], {"type": "retry_failed_chapter"})
        self.assertEqual(completed["state"], "complete")
        self.assertEqual(
            [c["status"] for c in self.repo.list_note_chapters(task["id"])],
            ["complete", "complete", "complete"],
        )

    def test_outline_note_structure_is_owned_by_the_workflow_not_chapter_markdown(self):
        class WholeNoteShapedChapterLLM(FakeLLM):
            def generate_chapter(self, task, chapter, previous_summary):
                return {
                    "content": (
                        "### 核心摘要\n\n这是模型擅自生成的本章摘要。\n\n"
                        "### 正文\n\n"
                        f"#### {chapter['title']}\n\n{chapter['title']}的独有正文。\n"
                    ),
                    "summary": "",
                }

            def generate_supplements(self, task, body_markdown):
                return {
                    "summary": "整份笔记只保留一次的核心摘要。",
                    "concepts": "- 关键概念只整理一次",
                    "actions": "- 实践提炼只整理一次",
                }

        llm = WholeNoteShapedChapterLLM()
        workflow = NoteWorkflow(self.repo, llm, run_in_background=False)
        task = workflow.start_analysis(
            {
                "device_id": "browser",
                "source": {
                    "type": "paste",
                    "name": "结构验收逐字稿",
                    "transcript": "依次说明控制欲根源、心理机制与关系练习。",
                },
                "request_text": "按篇章生成，不要重复摘要。",
            }
        )
        workflow.command(
            task["id"],
            {
                "type": "save_settings",
                "settings": {
                    "structure": "problem_solution",
                    "detail": "key",
                    "method": "outline",
                    "modules": ["summary", "concepts", "actions"],
                },
            },
        )
        outlined = workflow.command(task["id"], {"type": "start_generation"})
        completed = workflow.command(outlined["id"], {"type": "confirm_outline"})
        markdown = self.repo.get_note(completed["note_id"])["current_markdown"]

        self.assertEqual(markdown.count("# 亲密关系中的控制欲：三重根源与破解路径"), 1)
        self.assertEqual(
            [line.removeprefix("## ") for line in markdown.splitlines() if line.startswith("## ")],
            ["控制欲从何而来", "三重心理机制", "关系中的破解练习"],
        )
        self.assertNotRegex(markdown, r"(?m)^#{1,6}\s+(核心摘要|正文|关键概念|实践提炼)$")
        self.assertEqual(markdown.count("> **核心摘要**"), 1)
        self.assertEqual(markdown.count("**复习增强｜关键概念**"), 1)
        self.assertEqual(markdown.count("**复习增强｜实践提炼**"), 1)
        for title in ["控制欲从何而来", "三重心理机制", "关系中的破解练习"]:
            self.assertIn(f"{title}的独有正文。", markdown)

    def test_background_chapter_retry_leaves_failure_state_before_worker_runs(self):
        self.llm.fail_chapter_position = 1
        task = self.start_ready_task()
        self.workflow.command(
            task["id"],
            {"type": "save_settings", "settings": {"method": "outline", "detail": "complete"}},
        )
        outlined = self.workflow.command(task["id"], {"type": "start_generation"})
        failed = self.workflow.command(outlined["id"], {"type": "confirm_outline"})
        self.assertEqual(failed["state"], "chapter_failed")

        background_workflow = NoteWorkflow(self.repo, self.llm, run_in_background=True)
        with patch("vtn.workflows.notes.threading.Thread") as deferred_thread:
            retrying = background_workflow.command(
                task["id"], {"type": "retry_failed_chapter"}
            )

        self.assertEqual(retrying["state"], "generating_chapters")
        self.assertEqual(
            retrying["progress"],
            {"stage": "chapters", "completed": 0, "total": 3, "current_position": 1},
        )
        deferred_thread.assert_called_once()

    def test_two_outline_tasks_do_not_share_chapter_primary_keys(self):
        for _ in range(2):
            task = self.start_ready_task()
            self.workflow.command(
                task["id"],
                {"type": "save_settings", "settings": {"method": "outline", "detail": "complete"}},
            )
            self.workflow.command(task["id"], {"type": "start_generation"})
            completed = self.workflow.command(task["id"], {"type": "confirm_outline"})
            self.assertEqual(completed["state"], "complete")

    def test_every_generation_setting_keeps_the_same_document_structure_contract(self):
        structures = ["source_flow", "thematic", "problem_solution", "step_by_step"]
        details = ["quick", "key", "complete"]
        methods = ["direct", "outline"]
        module_ids = ["summary", "concepts", "actions", "review_questions"]
        module_sets = [
            list(selection)
            for size in range(len(module_ids) + 1)
            for selection in combinations(module_ids, size)
        ]

        for structure in structures:
            for detail in details:
                for method in methods:
                    for modules in module_sets:
                        with self.subTest(
                            structure=structure, detail=detail, method=method, modules=modules
                        ):
                            task = self.workflow.start_analysis(
                                {
                                    "device_id": "matrix-browser",
                                    "source": {
                                        "type": "paste",
                                        "name": "配置矩阵",
                                        "transcript": "用于验证全部生成设置结构稳定性的逐字稿。",
                                    },
                                }
                            )
                            self.workflow.command(
                                task["id"],
                                {
                                    "type": "save_settings",
                                    "settings": {
                                        "structure": structure,
                                        "detail": detail,
                                        "method": method,
                                        "modules": modules,
                                    },
                                },
                            )
                            generated = self.workflow.command(
                                task["id"], {"type": "start_generation"}
                            )
                            if method == "outline":
                                generated = self.workflow.command(
                                    task["id"], {"type": "confirm_outline"}
                                )
                            self.assertEqual(generated["state"], "complete")
                            markdown = self.repo.get_note(generated["note_id"])["current_markdown"]
                            self.assertEqual(len(re.findall(r"(?m)^#\s+", markdown)), 1)
                            h2 = re.findall(r"(?m)^##\s+(.+)$", markdown)
                            self.assertTrue(h2)
                            self.assertEqual(len(h2), len(set(h2)))
                            self.assertNotRegex(
                                markdown,
                                r"(?m)^#{1,6}\s+(核心摘要|正文|关键概念|实践提炼|复习问题)$",
                            )
                            expected_labels = {
                                "summary": "> **核心摘要**",
                                "concepts": "**复习增强｜关键概念**",
                                "actions": "**复习增强｜实践提炼**",
                                "review_questions": "**复习增强｜复习问题**",
                            }
                            for module_id, label in expected_labels.items():
                                self.assertEqual(markdown.count(label), int(module_id in modules))

    def test_generated_markdown_removes_preamble_and_raw_mermaid(self):
        raw = """好的，下面是笔记。\n\n# 标题\n\n## 关系图\n\n```mermaid\ngraph TD\nA[分离创伤] --> B[控制欲]\nB --> C[边界练习]\n```"""
        normalized = normalize_generated_markdown(raw, "标题")
        self.assertTrue(normalized.startswith("# 标题"))
        self.assertNotIn("好的，下面是笔记", normalized)
        self.assertNotIn("mermaid", normalized.lower())
        self.assertNotIn("graph TD", normalized)
        self.assertIn("分离创伤 → 控制欲", normalized)


if __name__ == "__main__":
    unittest.main()
