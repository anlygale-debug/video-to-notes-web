import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path

from vtn.domain.errors import DomainError
from vtn.llm_provider import llm_request, llm_response_text


STRUCTURE_CATALOG = {
    "source_flow": {
        "label": "沿原文脉络",
        "instruction": "保留讲述顺序和转折关系，按原内容的自然推进组织章节。",
    },
    "thematic": {
        "label": "按主题分类",
        "instruction": "打散口语顺序，将相关内容归并为清晰的主题章节。",
    },
    "problem_solution": {
        "label": "问题 → 原因 → 方法",
        "instruction": "先说明问题与表现，再解释原因，最后整理方法和行动建议。",
    },
    "step_by_step": {
        "label": "步骤教程",
        "instruction": "弱化叙事，按可执行步骤、注意事项和验收结果组织。",
    },
}

MODULE_CATALOG = {
    "summary": "核心摘要",
    "concepts": "关键概念",
    "actions": "实践提炼",
    "review_questions": "复习问题",
}

DETAIL_CATALOG = {
    "quick": {
        "label": "速查摘要",
        "instruction": "只保留框架、核心结论和必要行动，目标约为原文信息量的 5%-10%。",
    },
    "key": {
        "label": "要点提炼＋关键原话",
        "instruction": "提炼关键解释、方法和代表性案例，并在确有价值时保留讲述者的关键原话，目标约为原文信息量的 15%-20%。",
    },
    "complete": {
        "label": "完整详解",
        "instruction": "完整保留概念、推理链、方法步骤、重要案例和限制条件，目标约为原文信息量的 30%-40%。",
    },
}

MODULE_INSTRUCTIONS = {
    "summary": "在正文前提供简洁的全篇核心摘要。",
    "concepts": "整理关键概念及其定义；术语解释合并到这里。",
    "actions": "提炼可以执行的步骤、练习和案例启示。",
    "review_questions": "在文末提供少量能检验理解的复习问题。",
}

DEFAULT_MODULES = ["summary", "concepts", "review_questions"]

QUALITY_RULES = """质量规则：
- 默认使用简体中文整理笔记；只有逐字稿中的关键原话保留原语言，除非用户明确要求其他语言。
- 对原文确实包含的概念、推理、方法、案例、限制条件和注意事项应充分保留；不得把有解释过程的内容压成孤立结论。
- 删除口头禅、寒暄和重复表达，但不能删除承载新信息的细节。
- 删除广告、付费社群推广、关注引导和纯告别等与知识内容无关的信息；但有信息量的作业说明、作品展示、现场问答、课程预告和总结不能被当作片尾废话删除。
- 优先保留讲述者有辨识度且承载观点的关键原话、类比、比喻和具体案例；不要把所有内容改写成同一种教科书定义或清单。
- 关键原话应逐字来自逐字稿，并在确有助于理解或记忆时使用引用块；不要编造引语，也不要为凑数量硬加引用。
- 候选原话若含明显转录错误，不要把错误文本放进引用块；改用忠实转述，并按上下文统一 Skill、MCP、GitHub、Pull Request 等明确术语。
- 让写作形式服从内容关系：段落、列表、引用块和表格按需选用。只有两个以上对象且存在三个以上比较维度时才优先使用表格，不要为形式丰富强行制表。
- 内容密度服从信息价值：关键概念、推理、方法和案例充分展开，过渡与重复压缩；避免每章固定成相同长度、句式和模板。
- 原文有时间信息时可保留在确有助于回看之处；原文没有时不得虚构或强求时间范围。
- 不得补写逐字稿没有支持的事实；输出必须让用户不看原视频也能理解核心内容。
- 正文是主体；附加模块可以为零，只在确有额外价值时生成，不能取代或重复正文。"""


def generation_context(task):
    plan = task.get("final_settings") or {}
    return (
        f"本次笔记需求：{task.get('request_text') or '无'}\n"
        f"最终生成方案：{json.dumps(plan, ensure_ascii=False)}\n"
        f"{QUALITY_RULES}"
    )


def chapter_generation_context(task):
    plan = task.get("final_settings") or {}
    body_plan = {
        "structure": plan.get("structure") or {},
        "detail": plan.get("detail") or {},
        "method": plan.get("method") or "outline",
        "additional_request": plan.get("additional_request") or "",
    }
    return (
        f"本次笔记需求：{task.get('request_text') or '无'}\n"
        f"正文生成方案：{json.dumps(body_plan, ensure_ascii=False)}\n"
        f"{QUALITY_RULES}"
    )


def build_generation_plan(recommendation, selection=None):
    """Build the single persisted plan used by both recommended and custom generation."""
    recommendation = recommendation or {}
    selection = selection or {}
    recommended_structure = (recommendation.get("structure") or {}).get(
        "recommended_id", "source_flow"
    )
    structure_id = selection.get("structure") or recommended_structure
    if structure_id not in STRUCTURE_CATALOG:
        raise ValueError("请选择有效的笔记结构")

    recommended_detail = (recommendation.get("detail") or {}).get(
        "recommended_id", "complete"
    )
    detail_id = selection.get("detail") or recommended_detail
    if detail_id not in DETAIL_CATALOG:
        raise ValueError("请选择有效的详细程度")

    recommended_method = (recommendation.get("method") or {}).get(
        "recommended_id", "direct"
    )
    method = selection.get("method") or recommended_method
    if method not in {"direct", "outline"}:
        raise ValueError("请选择生成方式")

    if "modules" in selection:
        module_ids = selection.get("modules") or []
    else:
        module_ids = (recommendation.get("modules") or {}).get(
            "recommended_ids", DEFAULT_MODULES
        )
    unique_module_ids = []
    for module_id in module_ids:
        if module_id not in MODULE_CATALOG:
            raise ValueError("附加模块包含无效选项")
        if module_id not in unique_module_ids:
            unique_module_ids.append(module_id)
    if len(unique_module_ids) > 4:
        raise ValueError("附加模块最多选择 4 项")

    additional_request = str(selection.get("additional_request") or "").strip()
    if len(additional_request) > 2000:
        raise ValueError("其他要求不能超过 2000 字")

    return {
        "structure": {
            "id": structure_id,
            "label": STRUCTURE_CATALOG[structure_id]["label"],
            "instruction": STRUCTURE_CATALOG[structure_id]["instruction"],
        },
        "detail": {
            "id": detail_id,
            "label": DETAIL_CATALOG[detail_id]["label"],
            "instruction": DETAIL_CATALOG[detail_id]["instruction"],
        },
        "method": method,
        "modules": [
            {
                "id": module_id,
                "label": MODULE_CATALOG[module_id],
                "instruction": MODULE_INSTRUCTIONS[module_id],
            }
            for module_id in unique_module_ids
        ],
        "additional_request": additional_request,
    }


def normalize_recommendation(result):
    """Turn an LLM suggestion into the small, stable planning contract exposed by the API."""
    result = result if isinstance(result, dict) else {}
    title = str(result.get("title") or "未命名笔记").strip()
    reason = str(result.get("reason") or "已根据逐字稿内容准备推荐设置。").strip()

    raw_structure = result.get("structure") if isinstance(result.get("structure"), dict) else {}
    raw_option_ids = raw_structure.get("option_ids") or raw_structure.get("options") or []
    option_ids = []
    raw_options_by_id = {}
    for option in raw_option_ids:
        option_id = option.get("id") if isinstance(option, dict) else option
        if option_id in STRUCTURE_CATALOG and option_id not in option_ids:
            option_ids.append(option_id)
            if isinstance(option, dict):
                raw_options_by_id[option_id] = option
    recommended_structure = raw_structure.get("recommended_id")
    if recommended_structure in STRUCTURE_CATALOG and recommended_structure not in option_ids:
        option_ids.insert(0, recommended_structure)
    has_valid_custom_structure = len(option_ids) >= 2
    if len(option_ids) < 2:
        option_ids = ["source_flow", "thematic", "problem_solution"]
    option_ids = option_ids[:3]
    if recommended_structure not in option_ids:
        recommended_structure = option_ids[0]
    structure_reason = str(raw_structure.get("reason") or reason).strip()
    structure = {
        "question": str(
            (raw_structure.get("question") if has_valid_custom_structure else "")
            or "这份笔记最适合怎样组织？"
        ).strip(),
        "options": [
            {
                "id": option_id,
                "label": str(
                    raw_options_by_id.get(option_id, {}).get("label")
                    or STRUCTURE_CATALOG[option_id]["label"]
                ).strip(),
                "reason": str(
                    raw_options_by_id.get(option_id, {}).get("reason")
                    or STRUCTURE_CATALOG[option_id]["instruction"]
                ).strip(),
            }
            for option_id in option_ids
        ],
        "recommended_id": recommended_structure,
        "reason": structure_reason,
    }

    raw_detail = result.get("detail") if isinstance(result.get("detail"), dict) else {}
    recommended_detail = raw_detail.get("recommended_id")
    if recommended_detail not in {"quick", "key", "complete"}:
        recommended_detail = "complete"
    detail = {
        "question": str(
            raw_detail.get("question") or "这次需要保留多少解释、案例和原话？"
        ).strip(),
        "options": [
            {
                "id": detail_id,
                "label": DETAIL_CATALOG[detail_id]["label"],
                "reason": DETAIL_CATALOG[detail_id]["instruction"],
            }
            for detail_id in ("quick", "key", "complete")
        ],
        "recommended_id": recommended_detail,
        "reason": str(raw_detail.get("reason") or reason).strip(),
    }

    raw_method = result.get("method") if isinstance(result.get("method"), dict) else {}
    recommended_method = raw_method.get("recommended_id")
    if recommended_method not in {"direct", "outline"}:
        recommended_method = "direct"
    method = {
        "question": str(
            raw_method.get("question") or "生成正文前，要不要先确认大纲？"
        ).strip(),
        "options": [
            {
                "id": "direct",
                "label": "一次性生成",
                "reason": "适合结构清晰、篇幅较短或主题较少的内容。",
            },
            {
                "id": "outline",
                "label": "先确认大纲",
                "reason": "适合篇幅长、主题多或推理链复杂的内容。",
            },
        ],
        "recommended_id": recommended_method,
        "reason": str(raw_method.get("reason") or reason).strip(),
    }

    raw_modules = result.get("modules") if isinstance(result.get("modules"), dict) else {}
    selected_modules = []
    raw_recommended_modules = raw_modules.get("recommended_ids")
    if isinstance(raw_recommended_modules, list):
        for module_id in raw_recommended_modules:
            if module_id in MODULE_CATALOG and module_id not in selected_modules:
                selected_modules.append(module_id)
    elif "recommended_ids" not in raw_modules:
        # 兼容没有模块判断字段的旧任务；明确的空数组则代表“只要正文”。
        selected_modules = list(DEFAULT_MODULES)
    selected_modules = selected_modules[:3]
    raw_module_reasons = (
        raw_modules.get("reasons") if isinstance(raw_modules.get("reasons"), dict) else {}
    )
    modules = {
        "question": str(
            raw_modules.get("question") or "正文之外，还需要哪些复习工具？"
        ).strip(),
        "available_ids": list(MODULE_CATALOG),
        "recommended_ids": selected_modules,
        "reasons": {
            module_id: str(raw_module_reasons.get(module_id) or "与本次内容相关。")
            for module_id in selected_modules
        },
        "max_recommended": 3,
    }

    profile = result.get("profile") if isinstance(result.get("profile"), dict) else {}
    return {
        "title": title,
        "reason": reason,
        "profile": {
            "format": str(profile.get("format") or "纯文本流"),
            "length": str(profile.get("length") or "中等"),
            "content_type": str(profile.get("content_type") or "知识讲解"),
            "natural_structure": str(profile.get("natural_structure") or "按内容脉络推进"),
            "density": str(profile.get("density") or "中等"),
        },
        "structure": structure,
        "detail": detail,
        "method": method,
        "modules": modules,
    }


class LLM:
    def analyze(self, transcript, request_text):
        raise NotImplementedError

    def generate_direct(self, task):
        raise NotImplementedError

    def generate_outline(self, task, feedback=""):
        raise NotImplementedError

    def generate_chapter(self, task, chapter, previous_summary):
        raise NotImplementedError

    def generate_chapter_batch(self, task, chapters, completed_context):
        raise NotImplementedError

    def generate_supplements(self, task, body_markdown):
        return {}

    def check_integrity(self, task, markdown):
        return {"status": "ok"}


class OpenAICompatibleLLM(LLM):
    def __init__(self, settings_path, *, profile_id=None):
        from vtn.llm_provider import LLMProviderStore

        self.settings_store = (
            settings_path
            if isinstance(settings_path, LLMProviderStore)
            else LLMProviderStore(settings_path, default_enabled=True)
        )
        self.settings_path = self.settings_store.path
        self.profile_id = profile_id

    def _settings(self):
        return self.settings_store.credentials(self.profile_id)

    def active_profile_id(self):
        return self.settings_store.active_profile_id()

    def profile_id_for_channel(self, channel):
        return self.settings_store.profile_id_for_channel(channel)

    def generation_routes(self):
        return self.settings_store.generation_routes()

    def _analysis_timeout_seconds(self):
        try:
            channel = self._settings().get("channel")
        except DomainError:
            # Test doubles and unconfigured instances still fail in _complete;
            # timeout selection itself must not pre-empt that behavior.
            channel = None
        return 180 if channel == "free" else 90

    def for_profile(self, profile_id):
        return OpenAICompatibleLLM(
            self.settings_store,
            profile_id=profile_id or self.settings_store.active_profile_id(),
        )

    @staticmethod
    def _ssl_context():
        try:
            import certifi
            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            return ssl.create_default_context()

    def _complete(
        self,
        prompt,
        *,
        json_mode=False,
        max_tokens=8000,
        request_timeout_seconds=180,
        temperature=0.35,
    ):
        settings = self._settings()
        settings.setdefault("model", "deepseek-v4-pro")
        request = llm_request(
            settings,
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=json_mode,
        )
        try:
            with urllib.request.urlopen(
                request, timeout=request_timeout_seconds, context=self._ssl_context()
            ) as response:
                data = json.loads(response.read())
            return llm_response_text(settings, data)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise DomainError(
                    "LLM_AUTH_FAILED",
                    "AI 服务凭证无效或没有当前模型权限。",
                    retryable=False,
                ) from exc
            if exc.code == 429:
                raise DomainError(
                    "LLM_RATE_LIMITED",
                    "AI 服务当前请求较多，请稍后重新检查。",
                    retryable=True,
                ) from exc
            if exc.code >= 500:
                raise DomainError(
                    "LLM_SERVICE_UNAVAILABLE",
                    "AI 服务暂时不可用，请稍后重新检查。",
                    retryable=True,
                ) from exc
            raise DomainError(
                "LLM_REQUEST_FAILED",
                f"AI 请求失败（HTTP {exc.code}）。",
                retryable=False,
            ) from exc
        except TimeoutError as exc:
            raise DomainError(
                "LLM_TIMEOUT",
                "AI 服务响应超时，请稍后重新检查。",
                retryable=True,
            ) from exc
        except Exception as exc:
            raise DomainError("LLM_REQUEST_FAILED", f"AI 请求失败：{exc}", retryable=True)

    def _json(
        self,
        prompt,
        *,
        max_tokens=8000,
        request_timeout_seconds=180,
        temperature=0.35,
    ):
        try:
            completion_options = {"json_mode": True, "max_tokens": max_tokens}
            completion_options["temperature"] = temperature
            if request_timeout_seconds != 180:
                completion_options["request_timeout_seconds"] = request_timeout_seconds
            text = self._complete(prompt, **completion_options)
            stripped = text.strip()
            lines = stripped.splitlines()
            if (
                len(lines) >= 3
                and lines[0].strip().lower() in {"```", "```json"}
                and lines[-1].strip() == "```"
            ):
                stripped = "\n".join(lines[1:-1]).strip()
            try:
                return json.loads(stripped)
            except json.JSONDecodeError as exc:
                # Some reasoning models occasionally finish a complete JSON value and
                # then emit one redundant closing bracket. Recover only this narrow,
                # content-preserving case; prose or a second JSON value still fails.
                value, end = json.JSONDecoder().raw_decode(stripped)
                trailing = stripped[end:].strip()
                if trailing in {"]", "}"}:
                    return value
                raise exc
        except DomainError:
            raise
        except json.JSONDecodeError as exc:
            raise DomainError(
                "LLM_INVALID_RESPONSE",
                f"AI 返回格式无效：{exc}",
                retryable=True,
            ) from exc

    def analyze(self, transcript, request_text):
        analysis_timeout_seconds = self._analysis_timeout_seconds()
        try:
            result = self._json(
                "你是笔记生成前的内容规划器，不是出题器。先快速预读逐字稿，再返回严格 JSON。\n"
            "profile 必须判断 format、length、content_type、natural_structure、density。\n"
            "你要完成结构、详细程度、生成方式、附加模块四个判断。四个判断的 question、"
            "选项说明和推荐理由都必须结合本次逐字稿与用户用途来写，不能复制通用配置文案。\n"
            "structure 只决定笔记如何组织，绝不能提问逐字稿里的知识答案。"
            "structure.options 只能从 source_flow、thematic、problem_solution、step_by_step 中"
            "选择最相关的 2-3 个对象；每个对象包含 id、结合本次内容改写的 label 和 reason。"
            "recommended_id 必须来自 options，并给出本次专属的 question 与 reason。\n"
            "如果原文是已有清晰章节信号的课程、访谈或演讲，优先考虑 source_flow 以保留其递进、"
            "转折和首尾内容；只有原文明显散乱、重复或主题交错时才优先 thematic。\n"
            "detail.recommended_id 只能是 quick、key、complete；其中 key 表示‘要点提炼＋关键原话’。"
            "根据用户用途和内容密度判断，并给出本次专属的 question 与 reason。\n"
            "method.recommended_id 只能是 direct 或 outline。结构简单的短中内容可 direct；"
            "长、主题多或推理链复杂的内容推荐 outline，并给出本次专属的 question 与 reason。\n"
            "modules 只是正文之外的少量增强。请把 summary、concepts、actions、review_questions "
            "逐项独立判断，只推荐对本次内容确有额外价值的项目，并在 reasons 中逐项说明。"
            "recommended_ids 最多 3 个，也可以是空数组；空数组表示正文已经足够，只生成正文。"
            "默认优先只要正文，通常推荐 0-2 项：不要仅因原文较长就推荐 summary，不要仅因出现术语就推荐 concepts，"
            "不要仅因正文包含方法就推荐 actions，也不要在用户没有自测需求时推荐 review_questions。"
            "只有模块能产生正文无法自然承载的独立复习价值时才推荐；不要为了显得丰富而选择模块。\n"
            "返回字段：title、reason、profile、structure、detail、method、modules；"
            "structure、detail、method、modules 都必须包含 question。\n"
                f"本次笔记需求：{request_text or '无'}\n逐字稿：\n{transcript}",
                request_timeout_seconds=analysis_timeout_seconds,
                temperature=0.2,
            )
        except DomainError as exc:
            if exc.code == "LLM_TIMEOUT":
                raise DomainError(
                    "LLM_TIMEOUT",
                    f"AI 服务 {analysis_timeout_seconds} 秒内没有响应，已停止本次分析，请重试。",
                    retryable=True,
                ) from exc
            raise
        return normalize_recommendation(result)

    @staticmethod
    def _normalize_recommendation(result):
        return normalize_recommendation(result)

    def generate_direct(self, task):
        detail_id = ((task.get("final_settings") or {}).get("detail") or {}).get(
            "id", "complete"
        )
        max_tokens = {"quick": 6000, "key": 10000, "complete": 16000}.get(
            detail_id, 16000
        )
        modules = (task.get("final_settings") or {}).get("modules") or []
        module_ids = [module.get("id") for module in modules if module.get("id") in MODULE_CATALOG]
        supplement_schema = {module_id: "内容 Markdown，不要包含标题" for module_id in module_ids}
        data = self._json(
            "你是严谨的中文学习笔记编辑。依据逐字稿和最终生成方案，一次生成完整笔记的数据。\n"
            f"标题：{task['proposed_title']}\n{generation_context(task)}\n"
            "执行要求：\n"
            "- 先在内部通读全文并理解自然结构，再连续撰写完整文档；不要输出规划过程。\n"
            "- 严格执行方案中的结构说明和详细程度，不要把设置 ID 当作正文。\n"
            "- 正文是主体；附加模块仅在方案选中时生成，并保持简洁、不重复正文。\n"
            "- chapters 必须是互不重复、合起来覆盖全文的正文篇章；每章 content_markdown 不得包含篇章标题。\n"
            "- 每个概念、案例和方法只在一个主要篇章完整展开；原因篇不得提前代写方法篇。\n"
            "- 各章是同一份文档的连续部分，非末章不得各自生成全文总结、结语或全局注意事项。\n"
            "- content_markdown 内部标题只能从 ### 开始，不得输出核心摘要、正文或附加模块包装标题。\n"
            "- supplements 只包含用户选择的模块，不得重复正文，不得输出任何 # 标题。\n"
            '返回严格 JSON：{"chapters":[{"title":"篇章标题","content_markdown":"篇章正文"}],'
            f'"supplements":{json.dumps(supplement_schema, ensure_ascii=False)}}}。\n'
            f"逐字稿：\n{task['basis_transcript']}",
            max_tokens=max_tokens,
            temperature=0.5,
        )
        chapters = data.get("chapters") if isinstance(data.get("chapters"), list) else []
        supplements = data.get("supplements") if isinstance(data.get("supplements"), dict) else {}
        return {
            "chapters": [
                {
                    "title": str(chapter.get("title") or "").strip(),
                    "content_markdown": str(chapter.get("content_markdown") or ""),
                }
                for chapter in chapters if isinstance(chapter, dict)
            ],
            "supplements": {
                module_id: str(supplements.get(module_id) or "").strip()
                for module_id in module_ids
            },
        }

    def generate_outline(self, task, feedback=""):
        data = self._json(
            "你是整份笔记的内容架构师。请先通读逐字稿，再拟定覆盖完整的只读章节大纲。"
            "章节边界要遵循方案中的组织方式和原文的自然推进。\n"
            f"{generation_context(task)}\n"
            "大纲要求：\n"
            "- 只列真正有助于理解本章的 subtopics，数量由内容决定；不要为了版式统一而凑小标题。\n"
            "- 通读开头、中段和结尾，确保原文每个有独立信息价值的阶段都有归属；不能因为内容出现在后半段或结尾就省略。\n"
            "- 有信息量的作业说明、作品展示、现场问答、课程预告和总结应保留，可按信息密度压缩，但不得直接删除。\n"
            "- 同一个概念、案例或方法只能分配给一个主要章节；原因章节不得提前完整代写方法章节。\n"
            "- 第一章只建立必要背景，不得提前讲完后续所有章节。\n"
            "- 非末章不得设置全篇总结、结语、最终行动清单或全局注意事项。\n"
            "- 如果已选择核心摘要模块，正文大纲不得再创建同义的全篇摘要章节。\n"
            "- 各章合起来覆盖概念定义、推理、方法、案例和限制条件，但不得靠重复来追求完整。\n"
            "返回严格 JSON："
            '{"chapters":[{"id":"chapter-01","title":"章节标题","goal":"本章独占任务",'
            '"subtopics":["二级主题一","二级主题二"]}]}。'
            f"\n标题：{task['proposed_title']}"
            f"\n补充要求：{feedback or '无'}\n逐字稿：{task['basis_transcript']}"
            ,
            temperature=0.3,
        )
        return data["chapters"]

    def generate_chapter(self, task, chapter, previous_summary):
        outline = json.dumps(task.get("outline") or [], ensure_ascii=False)
        data = self._json(
            f"你只负责生成已确认大纲中的一个篇章：《{chapter['title']}》。\n"
            f"{chapter_generation_context(task)}\n"
            f"整份大纲：{outline}\n本章目标：{chapter.get('goal') or '完整覆盖本章内容'}\n"
            f"前文事实摘要：{previous_summary or '无'}\n"
            "硬性规则：只覆盖本章目标，不得代写大纲中其他篇章；不得输出整份笔记标题、"
            "本章标题、核心摘要、正文、关键概念、实践提炼或复习问题等包装标题。"
            "content_markdown 内部小标题只能从 ### 开始。context_summary 只写本章新事实，"
            "不得包含 Markdown 标题或格式说明。\n"
            '返回严格 JSON：{"content_markdown":"本章正文 Markdown","context_summary":"供下一章衔接的事实摘要"}。\n'
            f"逐字稿：{task['basis_transcript']}",
            max_tokens=12000,
            temperature=0.5,
        )
        return {
            "content": str(data.get("content_markdown") or ""),
            "summary": str(data.get("context_summary") or "").strip(),
        }

    def generate_chapter_batch(self, task, chapters, completed_context):
        outline = json.dumps(task.get("outline") or [], ensure_ascii=False)
        batch_plan = [
            {
                "id": chapter.get("outline_id"),
                "title": chapter.get("title"),
                "goal": chapter.get("goal"),
                "subtopics": chapter.get("subtopics") or [],
            }
            for chapter in chapters
        ]
        detail_id = ((task.get("final_settings") or {}).get("detail") or {}).get(
            "id", "complete"
        )
        max_tokens = {"quick": 8000, "key": 12000, "complete": 16000}.get(
            detail_id, 16000
        )
        data = self._json(
            "你正在同一份笔记中连续撰写一组相邻章节，不是在回答多个彼此独立的问题。\n"
            f"{chapter_generation_context(task)}\n"
            f"整份已确认大纲：{outline}\n"
            f"本批章节计划：{json.dumps(batch_plan, ensure_ascii=False)}\n"
            f"已经完成的前文（首批则为无）：\n{completed_context or '无'}\n"
            "执行规则：\n"
            "- 严格按照本批章节顺序连续写作，并使用各章 subtopics 组织 ### 小标题。\n"
            "- 每个事实、案例和方法只在其归属章节完整展开；不得复述已完成前文，不得提前代写后续章节。\n"
            "- 章节之间自然承接，但不要使用‘上一章讲了’等机械串场句。\n"
            "- 每章是整份文档的一部分，不得各自生成全文摘要、结语、最终行动清单或全局注意事项。\n"
            "- 只有整份大纲的最后一章可以按原文需要收束全文；若选择了核心摘要模块，正文仍不得重复该摘要。\n"
            "- content_markdown 不得包含整份笔记标题或本章标题，内部标题只能从 ### 开始。\n"
            "- context_summary 只记录本章新写入的事实，供后续批次避免重复。\n"
            "返回严格 JSON，chapters 数量、id 和顺序必须与本批计划完全一致："
            '{"chapters":[{"id":"chapter-01","content_markdown":"正文 Markdown",'
            '"context_summary":"本章新增事实"}]}。\n'
            f"逐字稿：\n{task['basis_transcript']}",
            max_tokens=max_tokens,
            temperature=0.5,
        )
        raw_chapters = data.get("chapters") if isinstance(data, dict) else None
        if not isinstance(raw_chapters, list):
            raise DomainError("LLM_INVALID_RESPONSE", "AI 未返回完整的连续章节", retryable=True)
        return [
            {
                "id": str(result.get("id") or "").strip(),
                "content": str(result.get("content_markdown") or ""),
                "summary": str(result.get("context_summary") or "").strip(),
            }
            for result in raw_chapters if isinstance(result, dict)
        ]

    def generate_supplements(self, task, body_markdown):
        modules = (task.get("final_settings") or {}).get("modules") or []
        module_ids = [module.get("id") for module in modules if module.get("id") in MODULE_CATALOG]
        if not module_ids:
            return {}
        schema = {module_id: "Markdown 内容，不要包含标题" for module_id in module_ids}
        data = self._json(
            "正文篇章已经全部生成。现在只生成用户选择的复习增强内容。\n"
            f"本次选择：{json.dumps(module_ids, ensure_ascii=False)}\n"
            f"模块要求：{json.dumps({module_id: MODULE_INSTRUCTIONS[module_id] for module_id in module_ids}, ensure_ascii=False)}\n"
            "附加模块必须把正文转换成便于检索或练习的二阶形式，例如概念卡、判断规则、"
            "行动卡或测试题；不得换一种措辞复述正文段落，不得输出任何 # 标题，不得增加未选择的模块。"
            f"返回严格 JSON：{json.dumps(schema, ensure_ascii=False)}。\n"
            f"完整正文：\n{body_markdown}",
            max_tokens=8000,
            temperature=0.3,
        )
        return {module_id: str(data.get(module_id) or "").strip() for module_id in module_ids}

    def check_integrity(self, task, markdown):
        try:
            return self._json(
                "根据逐字稿、用户需求和最终生成方案检查笔记。"
                "确认正文是否覆盖概念定义、推理链、方法、案例与限制条件，"
                "并确认所有选中的附加模块已经兑现。不要用字数比例冒充覆盖率。\n"
                f"{generation_context(task)}\n"
                '只返回严格 JSON：{"status":"ok"} 或 '
                '{"status":"possible_omission","items":[{"source_locator":"","summary":"","chapter_id":""}]}。'
                f"\n逐字稿：{task['basis_transcript']}\n笔记：{markdown}",
                temperature=0.1,
            )
        except DomainError as exc:
            return {
                "status": "check_unavailable",
                "check_failed": True,
                "error_code": exc.code,
                "error_message": exc.message,
                "retryable": exc.retryable,
            }


class FakeLLM(LLM):
    def __init__(self):
        self.fail_chapter_position = None

    def analyze(self, transcript, request_text):
        return {
            "title": "亲密关系中的控制欲：三重根源与破解路径",
            "reason": "内容适合按根源、表现与练习组织。",
            "structure": {
                "option_ids": ["problem_solution", "thematic", "source_flow"],
                "recommended_id": "problem_solution",
                "reason": "内容同时包含问题、成因和行动方法。",
            },
            "detail": {"options": ["quick", "key", "complete"], "recommended_id": "complete"},
            "method": {"options": ["direct", "outline"], "recommended_id": "direct"},
            "modules": {"recommended_ids": DEFAULT_MODULES, "reasons": {}},
        }

    def generate_direct(self, task):
        return {
            "chapters": [
                {
                    "title": "控制欲从何而来",
                    "content_markdown": "亲密关系中的控制欲常与分离创伤、客体认同和认知固化有关。",
                },
                {
                    "title": "行动方法",
                    "content_markdown": "- 识别触发点\n- 区分需要与控制\n- 练习稳定表达",
                },
            ],
            "supplements": self.generate_supplements(task, ""),
        }

    def generate_outline(self, task, feedback=""):
        suffix = "（补充失败复盘）" if feedback else ""
        return [
            {"id": "chapter-01", "title": "控制欲从何而来", "goal": "理解根源"},
            {"id": "chapter-02", "title": "三重心理机制", "goal": "拆解机制"},
            {"id": "chapter-03", "title": f"关系中的破解练习{suffix}", "goal": "形成行动"},
        ]

    def generate_chapter(self, task, chapter, previous_summary):
        try:
            position = int(chapter["id"].split("-")[-1])
        except ValueError:
            position = 1
        if self.fail_chapter_position == position:
            raise DomainError("CHAPTER_GENERATION_FAILED", "章节生成失败", retryable=True)
        content = f"## {chapter['title']}\n\n这是第 {position} 章的完整内容。\n"
        return {"content": content, "summary": f"第 {position} 章已说明 {chapter['title']}"}

    def generate_supplements(self, task, body_markdown):
        selected = {
            module["id"] for module in (task.get("final_settings") or {}).get("modules", [])
        }
        values = {
            "summary": "控制欲需要从根源、机制和练习三个层面理解。",
            "concepts": "- 分离创伤：关系中的失去恐惧。",
            "actions": "- 记录触发点，并练习表达真实需求。",
            "review_questions": "- 控制冲动背后可能有哪些真实需求？",
        }
        return {module_id: values[module_id] for module_id in selected if module_id in values}
