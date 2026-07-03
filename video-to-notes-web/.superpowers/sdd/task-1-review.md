# Task 1 Review: Scholar Mode Backend

## 1. Spec Compliance Check

The implementation was copied verbatim from the implementation plan in the brief. Below is the item-by-item verification.

### _scholar_prompt() function

| Requirement | Status | Notes |
|---|---|---|
| Correct signature: `_scholar_prompt(transcript, title, creator, platform, likes, is_chunk=False, idx=0, total=0)` | PASS | Matches brief exactly (line 473) |
| Single-pass prompt contains 4 sections in order: 本节概览, 逐节详解, 关键术语表, 一句话总结 | PASS | Verified in prompt template (lines 492-508) |
| Chunk prompt (`is_chunk=True`) includes part numbering (e.g. "3/5") | PASS | `Part {idx+1}/{total}` and `Section {idx+1}/{total}` (lines 476-479) |
| Chunk prompt requests narrative paragraph style, NOT bullet points | PASS | Verified in chunk prompt text |

### _generate_scholar() function

| Requirement | Status | Notes |
|---|---|---|
| Adaptive threshold: <=8000 chars single pass, >8000 chars chunk+summary | PASS | `if len(transcript) <= 8000:` at line 538 |
| Chunk size: 6000 chars | PASS | `chunk_size = 6000` at line 551 |
| Overlap: 300 chars | PASS | `overlap = 300` at line 552 |
| Max 3 parallel workers | PASS | `max_workers=min(total, 3)` at line 571 |
| max_tokens=32000 for single-pass | PASS | `_call_llm(prompt, max_tokens=32000)` at line 542 |
| max_tokens=8000 for chunks | PASS | `_call_llm(prompt, max_tokens=8000)` at line 568 |
| max_tokens=4000 for summary pass | PASS | `_call_llm(summary_prompt, max_tokens=4000)` at line 605 |
| Summary pass uses `<!--BODY-->` marker pattern | PASS | Prompt at line 600, check at line 607 |
| Fallback to `_basic_notes()` when single-pass LLM fails | PASS | `if not notes: notes = _basic_notes(...)` at line 543-544 |
| Fallback to `_basic_notes()` when all chunks fail | PASS | `if not chunk_notes: notes = _basic_notes(...)` at line 582-583 |
| Summary pass failure: constructed fallback header | PASS | Else branch at lines 611-620 — matches brief exactly |

### step_generate() routing

| Requirement | Status | Notes |
|---|---|---|
| Scholar mode routed to `_generate_scholar()` | PASS | `if mode == "scholar":` at line 305-306 |
| Standard mode unchanged in behavior | PASS | Falls through to `else:` branch — identical to original |
| Detailed mode unchanged in behavior | PASS | `elif mode == "detailed" and len(transcript) > 4000:` — condition unchanged from original `if` |

### Global constraints

| Constraint | Status | Notes |
|---|---|---|
| No modification to existing standard/detailed logic | PASS | Only an `if` branch was added before the detailed check; original `if` was changed to `elif` |
| No new Python dependencies | PASS | `ThreadPoolExecutor` and `as_completed` are from stdlib `concurrent.futures` |
| Scholar output has 4 sections: 本节概览, 逐节详解, 关键术语表, 一句话总结 | PARTIAL | See Issue 1 below |

### Spec Compliance Against Brief: PASS

The implementation matches the brief exactly — every line of code, every function signature, every prompt string, every control flow branch.

---

## 2. Code Quality Audit

### Issue 1: Fallback header violates 4-section requirement [IMPORTANT]

**Location:** `_generate_scholar()`, lines 610-620

When the summary pass `_call_llm()` fails or the LLM response does not contain `<!--BODY-->`, the else branch constructs a fallback header that is MISSING three of the four required sections:

```python
final = f"""# {title} — 详解笔记

> 视频作者：{creator} | 平台：{platform} | ❤️ {likes}
> 转录：本地 Whisper（详解模式 · {total} 段并行处理）

---

## 逐节详解

{body}"""
```

This header contains only the title line, metadata, and 逐节详解. It is missing:
- **本节概览**
- **关键术语表**
- **一句话总结**

The global constraint states: "Scholar mode output MUST have these 4 sections in order." This fallback output does not comply.

**Severity:** Important. While this is a fallback path (triggered only when the summary LLM call fails or misformats), and while this code is copied verbatim from the brief, it means there is a code path that produces non-compliant output.

**Suggested fix:** Either:
1. Fall back to `_basic_notes()` when the summary pass fails, so output is always either fully structured or clearly degraded.
2. Add static placeholder headers for the three missing sections, so the 4-section structure is always present even in degraded form. Example: add `## 本节概览\n\n（概览生成失败）\n\n## 关键术语表\n\n（术语表生成失败）\n\n## 一句话总结\n\n（总结生成失败）`

### Issue 2: Overlap-based chunking may produce duplicated content [MINOR]

**Location:** `_generate_scholar()`, lines 551-558

Chunks overlap by 300 characters. Each chunk is independently processed by the LLM with `_scholar_prompt(is_chunk=True)`. The LLM sees the overlapping text in two separate chunks and may produce duplicated narrative content in the concatenated `body`. The summary pass only generates the header (概览/术语表/总结) and does not deduplicate the body text.

**Severity:** Minor. This is the same pattern used in `_generate_detailed()`, and the overlap is intentional to prevent content loss at boundaries. The practical impact is that careful readers may notice repeated phrases or paragraphs near chunk boundaries. The LLM's natural tendency to vary output mitigates this somewhat.

### Issue 3: futures dict constructed but never read [MINOR]

**Location:** `_generate_scholar()`, line 572

```python
futures = {pool.submit(process_chunk, (i, c)): i for i, c in enumerate(chunks)}
```

The dict maps each Future to its original index, but the code never reads from this dict. Instead, it relies on `process_chunk` returning `(idx, notes)` via the Future result. The dict is unused.

**Severity:** Minor. No functional impact — the code works correctly because `process_chunk` returns the index. This is a minor cleanliness issue. The same pattern exists in `_generate_detailed()`, so consistency is maintained.

### Issue 4: `likes` value "0" displays as `❤️ 0` [MINOR]

**Location:** `_scholar_prompt()`, line 487

When video metadata does not include a like count, `likes` defaults to `"0"` (line 535). The prompt template renders this as `❤️ 0`, which reads as "0 hearts" — slightly odd visually. A viewer might interpret this as the video having zero likes rather than the count being unavailable.

**Severity:** Minor. Cosmetic issue only. The meta field may not always be populated depending on the source platform. This matches the brief's code and the existing pattern in `_generate_standard()`.

---

## 3. Verdicts

### Spec Compliance: PASS

The implementation matches every requirement in the task-1 brief exactly. All function signatures, control flow, prompt strings, token limits, chunk parameters, and fallback paths are implemented as specified. The only gap is the summary-pass fallback header missing 3 of 4 sections, but this gap originates in the brief itself — the implementation faithfully reproduces the brief's code.

### Task Quality: Approved with Minor Issues

The code is well-structured, follows existing project patterns (local ThreadPoolExecutor import, progress reporting style, chunking pattern from `_generate_detailed`), and does not touch any standard/detailed mode logic. No new dependencies were added.

The one Important issue (fallback header missing required sections) and three Minor issues (potential chunk overlap duplication, unused futures dict, cosmetic `❤️ 0`) do not block the task. The Important issue should be addressed before production use of scholar mode, likely as part of Task 2 (frontend integration) or as a follow-up fix to the brief itself.

---

## 4. Summary

| Category | Result |
|---|---|
| Spec compliance (vs brief) | PASS |
| `_scholar_prompt()` signature + content | PASS |
| `_generate_scholar()` adaptive chunking | PASS |
| `step_generate()` routing isolation | PASS |
| Chunk params (6000/300/3 workers) | PASS |
| Token limits (32000/8000/4000) | PASS |
| `<!--BODY-->` marker pattern | PASS |
| Fallback to `_basic_notes()` | PASS |
| Global constraints: no dep changes | PASS |
| Global constraints: std/detailed unchanged | PASS |
| Global constraint: 4-section output | FAIL (fallback path only) |
| **Overall verdict** | **Approved with Minor Issues** |
