# Task 1 Report: Add scholar mode to app.py

## Status: DONE

All three steps from the plan have been implemented exactly as specified. Code was copied verbatim from the implementation plan -- no redesign, no section renaming, no prompt restructuring.

## Changes Made

### 1. Added `_scholar_prompt()` helper function (line 473-531)
- Generates the scholar-mode prompt with essay-style narrative structure
- Supports two modes via `is_chunk` flag:
  - `is_chunk=False` (default): single-pass prompt with the full transcript
  - `is_chunk=True`: chunk-aware prompt that includes part numbering (e.g., "3/5")
- Prompt sections: 本节概览, 逐节详解, 关键术语表, 一句话总结 -- EXACTLY as specified in the plan

### 2. Added `_generate_scholar()` function (line 534-625)
- Adaptive chunking with 8000-char threshold:
  - <=8000 chars: single LLM pass (`_call_llm(prompt, max_tokens=32000)`)
  - >8000 chars: chunk at 6000 chars with 300-char overlap, process chunks in parallel (ThreadPoolExecutor, max 3 workers), then summary pass to generate header (概览/术语表/总结) concatenated with chunk bodies
- Fallback to `_basic_notes()` if all LLM calls fail
- If summary pass fails, concatenates chunks directly with a generated header as second fallback
- Progress reporting mirrors the `_generate_detailed` pattern

### 3. Updated `step_generate()` (line 295-310)
- Added `"scholar"` mode to the docstring
- New branch: `if mode == "scholar": return _generate_scholar(...)`
- Existing `"standard"` and `"detailed"` modes are completely untouched

## Commits

- `f37a835` feat: add scholar mode with adaptive chunking for reading-based notes

## Test Summary

| Test | Result |
|------|--------|
| Python syntax check (ast.parse) | PASS |
| `_scholar_prompt()` exists and is callable | PASS |
| `_generate_scholar()` exists and is callable | PASS |
| `step_generate()` contains scholar branch | PASS |
| Single-pass prompt contains all 4 sections (本节概览/逐节详解/关键术语表/一句话总结) | PASS |
| Chunk prompt contains correct part numbering (e.g., "3/5") | PASS |
| `_scholar_prompt()` uses `max_tokens=32000` for single-pass | PASS |
| `_generate_scholar()` uses 8000-char threshold for adaptive chunking | PASS |
| `_basic_notes()` fallback path exists in `_generate_scholar()` | PASS |
| Standard mode still works (unchanged) | PASS |
| Detailed mode still works (unchanged) | PASS |

## Concerns

None.

- No new Python dependencies added.
- `ThreadPoolExecutor` is imported locally (same pattern as `_generate_detailed`).
- The summary pass for chunked scholar mode uses one extra LLM call compared to detailed mode -- this is intentional per the plan for generating the coherent header with 概览/术语表/总结.
- Code was copied exactly from the implementation plan. No prompt sections were renamed, no structure was redesigned.
