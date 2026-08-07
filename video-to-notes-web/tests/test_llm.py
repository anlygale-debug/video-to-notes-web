import json
import io
import unittest
import urllib.error
from unittest.mock import patch

from vtn.adapters.llm import OpenAICompatibleLLM
from vtn.domain.errors import DomainError


class CapturingLLM(OpenAICompatibleLLM):
    def __init__(self):
        super().__init__("/tmp/unused-vtn-settings.json")
        self.prompts = []

    def _complete(self, prompt, *, json_mode=False, max_tokens=8000, **_options):
        self.prompts.append({"prompt": prompt, "json_mode": json_mode, "max_tokens": max_tokens})
        if json_mode and "possible_omission" in prompt:
            return json.dumps({"status": "ok"}, ensure_ascii=False)
        if json_mode:
            return json.dumps(
                {
                    "chapters": [
                        {"id": "chapter-01", "title": "第一章", "goal": "完整理解"}
                    ]
                },
                ensure_ascii=False,
            )
        return "# 测试笔记\n\n## 正文\n\n完整内容。"


class LLMGenerationContractTests(unittest.TestCase):
    def test_anthropic_messages_profile_uses_the_local_fcc_protocol(self):
        class FCCConfiguredLLM(OpenAICompatibleLLM):
            def _settings(self):
                return {
                    "api_base": "http://127.0.0.1:8082",
                    "api_key": "fcc-local-token",
                    "model": "claude-sonnet-4-5",
                    "protocol": "anthropic_messages",
                }

        captured = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(
                    {"content": [{"type": "text", "text": "FCC 已连接"}]}
                ).encode("utf-8")

        def respond(request, timeout, context=None):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data)
            return Response()

        with patch("urllib.request.urlopen", respond):
            result = FCCConfiguredLLM("/tmp/unused-settings.json")._complete(
                "测试免费线路", max_tokens=50, temperature=0.2
            )

        self.assertEqual(result, "FCC 已连接")
        self.assertEqual(captured["url"], "http://127.0.0.1:8082/v1/messages")
        self.assertEqual(captured["body"]["model"], "claude-sonnet-4-5")
        self.assertEqual(captured["body"]["messages"][0]["content"], "测试免费线路")
        self.assertIn("X-api-key", captured["headers"])

    def test_json_parser_accepts_a_single_markdown_json_fence(self):
        class FencedJsonLLM(CapturingLLM):
            def _complete(self, prompt, *, json_mode=False, max_tokens=8000, **_options):
                return '```json\n{"status":"ok","items":[]}\n```'

        result = FencedJsonLLM()._json("返回严格 JSON")

        self.assertEqual(result, {"status": "ok", "items": []})

    def test_json_parser_accepts_one_redundant_closing_bracket(self):
        class RedundantBracketLLM(CapturingLLM):
            def _complete(self, prompt, *, json_mode=False, max_tokens=8000, **_options):
                return '```json\n{"status":"ok","items":[]}\n]\n```'

        result = RedundantBracketLLM()._json("返回严格 JSON")

        self.assertEqual(result, {"status": "ok", "items": []})

    def test_json_parser_rejects_arbitrary_text_after_the_payload(self):
        class TrailingProseLLM(CapturingLLM):
            def _complete(self, prompt, *, json_mode=False, max_tokens=8000, **_options):
                return '{"status":"ok"}\n这里再补充一段说明'

        with self.assertRaises(DomainError) as failure:
            TrailingProseLLM()._json("返回严格 JSON")

        self.assertEqual(failure.exception.code, "LLM_INVALID_RESPONSE")

    def test_analysis_stops_after_a_short_request_timeout(self):
        class ConfiguredLLM(OpenAICompatibleLLM):
            def _settings(self):
                return {
                    "api_base": "https://api.example.test",
                    "api_key": "test-key",
                    "model": "test-model",
                }

        observed_timeouts = []

        def timeout_request(request, timeout, context=None):
            observed_timeouts.append(timeout)
            raise TimeoutError("controlled analysis timeout")

        with patch("urllib.request.urlopen", timeout_request):
            with self.assertRaises(DomainError) as failure:
                ConfiguredLLM("/tmp/unused-settings.json").analyze(
                    "一份需要预读的长逐字稿。", "用于复习"
                )

        self.assertEqual(observed_timeouts, [90])
        self.assertEqual(failure.exception.code, "LLM_TIMEOUT")
        self.assertIn("90 秒内没有响应", failure.exception.message)

    def test_free_channel_allows_slow_model_more_time_for_analysis(self):
        class FreeConfiguredLLM(OpenAICompatibleLLM):
            def _settings(self):
                return {
                    "api_base": "http://127.0.0.1:8082",
                    "api_key": "test-key",
                    "model": "test-model",
                    "channel": "free",
                }

        observed_timeouts = []

        def timeout_request(request, timeout, context=None):
            observed_timeouts.append(timeout)
            raise TimeoutError("controlled free analysis timeout")

        with patch("urllib.request.urlopen", timeout_request):
            with self.assertRaises(DomainError) as failure:
                FreeConfiguredLLM("/tmp/unused-free-settings.json").analyze(
                    "一份需要预读的长逐字稿。", "用于复习"
                )

        self.assertEqual(observed_timeouts, [180])
        self.assertEqual(failure.exception.code, "LLM_TIMEOUT")
        self.assertIn("180 秒内没有响应", failure.exception.message)

    def test_generation_request_failure_is_reported_without_hidden_retry(self):
        class FailFastLLM(OpenAICompatibleLLM):
            def __init__(self):
                super().__init__("/tmp/unused-vtn-settings.json")
                self.calls = 0

            def _complete(self, prompt, *, json_mode=False, max_tokens=8000, **_options):
                self.calls += 1
                raise DomainError(
                    "LLM_TIMEOUT",
                    "AI 服务响应超时，已停止本次生成。",
                    retryable=True,
                )

        llm = FailFastLLM()
        task = {
            "proposed_title": "测试笔记",
            "basis_transcript": "测试逐字稿",
            "request_text": "",
            "final_settings": {},
        }

        with self.assertRaises(DomainError) as failure:
            llm.generate_outline(task)

        self.assertEqual(failure.exception.code, "LLM_TIMEOUT")
        self.assertEqual(llm.calls, 1)

    def test_integrity_check_identifies_rate_limit_as_retryable(self):
        class ConfiguredLLM(OpenAICompatibleLLM):
            def _settings(self):
                return {
                    "api_base": "https://api.example.test",
                    "api_key": "test-key",
                    "model": "test-model",
                }

        def reject_request(request, timeout, context=None):
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "Too Many Requests",
                {},
                io.BytesIO(b'{"error":"rate limited"}'),
            )

        with patch("urllib.request.urlopen", reject_request):
            result = ConfiguredLLM("/tmp/unused-settings.json").check_integrity(
                {
                    "basis_transcript": "生成依据逐字稿",
                    "request_text": "用于复习",
                    "final_settings": {},
                },
                "# 测试笔记\n\n正文",
            )

        self.assertEqual(result["status"], "check_unavailable")
        self.assertEqual(result["error_code"], "LLM_RATE_LIMITED")
        self.assertTrue(result["retryable"])

    def test_integrity_check_preserves_safe_request_failure_details(self):
        class FailedIntegrityLLM(CapturingLLM):
            def _complete(self, prompt, *, json_mode=False, max_tokens=8000, **_options):
                raise DomainError(
                    "LLM_REQUEST_FAILED",
                    "AI 请求失败：测试连接超时",
                    retryable=True,
                )

        result = FailedIntegrityLLM().check_integrity(
            {
                "basis_transcript": "生成依据逐字稿",
                "request_text": "用于复习",
                "final_settings": {},
            },
            "# 测试笔记\n\n正文",
        )

        self.assertEqual(result["status"], "check_unavailable")
        self.assertTrue(result["check_failed"])
        self.assertEqual(result["error_code"], "LLM_REQUEST_FAILED")
        self.assertEqual(result["error_message"], "AI 请求失败：测试连接超时")
        self.assertTrue(result["retryable"])

    def test_every_generation_stage_receives_the_same_complete_plan_and_quality_rules(self):
        llm = CapturingLLM()
        task = {
            "proposed_title": "测试笔记",
            "request_text": "用于深入复习",
            "basis_transcript": "原文包含概念定义、推理过程、案例和行动方法。",
            "outline": [{"id": "chapter-01", "title": "第一章", "goal": "完整理解"}],
            "final_settings": {
                "structure": {
                    "id": "thematic",
                    "label": "按主题分类",
                    "instruction": "将相关内容归并为清晰的主题章节。",
                },
                "detail": {
                    "id": "complete",
                    "label": "完整详解",
                    "instruction": "完整保留概念、推理链、方法步骤、重要案例和限制条件。",
                },
                "method": "outline",
                "modules": [
                    {"id": "summary", "label": "核心摘要", "instruction": "提供全篇摘要。"},
                    {"id": "actions", "label": "实践提炼", "instruction": "提炼行动。"},
                ],
                "additional_request": "多保留失败案例。",
            },
        }

        llm.generate_direct(task)
        llm.generate_outline(task)
        llm.generate_chapter(task, task["outline"][0], "前文摘要")
        llm.check_integrity(task, "# 测试笔记\n\n正文")

        self.assertEqual(len(llm.prompts), 4)
        for captured in llm.prompts:
            prompt = captured["prompt"]
            self.assertIn("按主题分类", prompt)
            self.assertIn("完整详解", prompt)
            self.assertIn("核心摘要", prompt)
            self.assertIn("实践提炼", prompt)
            self.assertIn("多保留失败案例", prompt)
            self.assertIn("概念定义", prompt)
        self.assertIn("正文是主体", llm.prompts[0]["prompt"])
        self.assertIn("默认使用简体中文", llm.prompts[0]["prompt"])
        self.assertIn("广告", llm.prompts[0]["prompt"])
        self.assertIn("讲述者", llm.prompts[0]["prompt"])
        self.assertIn("关键原话", llm.prompts[0]["prompt"])
        self.assertIn("类比", llm.prompts[0]["prompt"])
        self.assertIn("同一种教科书定义或清单", llm.prompts[0]["prompt"])
        self.assertIn("有时间信息时可保留", llm.prompts[0]["prompt"])
        self.assertIn("没有时不得虚构或强求", llm.prompts[0]["prompt"])
        self.assertIn("作品展示", llm.prompts[0]["prompt"])
        self.assertNotIn("每章提供 2-5 个", llm.prompts[1]["prompt"])
        self.assertIn("开头、中段和结尾", llm.prompts[1]["prompt"])
        self.assertIn("不得直接删除", llm.prompts[1]["prompt"])
        self.assertNotIn("正文是主体，至少占成品的 75%", llm.prompts[0]["prompt"])
        self.assertIn("严格 JSON", llm.prompts[-1]["prompt"])

    def test_analysis_prompt_allows_ai_to_recommend_body_only(self):
        llm = CapturingLLM()

        llm.analyze("一份结构完整的短逐字稿。", "用于复习")

        prompt = llm.prompts[0]["prompt"]
        self.assertIn("recommended_ids 最多 3 个，也可以是空数组", prompt)
        self.assertIn("只生成正文", prompt)
        self.assertIn("逐项独立判断", prompt)
        self.assertIn("四个判断的 question", prompt)
        self.assertIn("结合本次逐字稿", prompt)
        self.assertIn("优先考虑 source_flow", prompt)
        self.assertIn("默认优先只要正文", prompt)


if __name__ == "__main__":
    unittest.main()
