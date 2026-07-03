# Task 2 Review: Text input support in /api/process

## Verdict: MERGE WITH FIX

One confirmed bug (incorrect `platform` in text-mode complete event). Several minor spec deviations are cosmetic and safe. Otherwise the implementation is clean and the fixup commit correctly resolved the `"skipped"` status issue.

---

## 1. Spec Compliance

### Requirements checklist

| Requirement | Status | Notes |
|---|---|---|
| Accept optional `text` body param | PASS | `body.get("text", "").strip()` at line 683 |
| Validate `not url and not text` returning 400 | PASS | Line 685-686 |
| Text mode skips resolve/download/transcribe pipeline | PASS | Lines 695-709 |
| Existing URL processing flow unchanged | PASS | Lines 721-743, identical logic |
| `step_generate` shared for both paths | PASS | Line 746 |
| Progress events use status `"done"` (post-fixup) | PASS | Lines 697, 702, 707 |
| Finally block safe for text mode (no audio_path) | PASS | Line 757, `.get("audio_path", "")` |
| Default `creator` = `""` | PASS | Line 714 |
| Default `title` = `"Untitled"` | PASS | Line 713 |
| `meta["platform"]` = `"text"` in text mode | PASS | Line 715 |
| `meta["likes"]` = `"0"` in text mode | PASS | Line 716 |

### Requirements with issues

| Requirement | Status | Detail |
|---|---|---|
| Complete event `meta.platform` = `"text"` for text mode | **FAIL** | See Bug 1 below |
| Progress event `message` = `"skipped"` | MINOR | Defined as `"Text input mode"`, cosmetic |
| `tasks[task_id]["url"]` uses `"(text input)"` fallback | MINOR | Uses bare `url` (empty string), cosmetic |
| Docstring: `"download → transcribe → notes"` | MINOR | `"→ transcribe → notes"` (missing `download`), cosmetic |

---

## 2. Bugs Found

### Bug 1: `platform` field in complete event is wrong for text mode

**Severity:** MEDIUM -- incorrect metadata returned to frontend.

**Location:** `app.py`, line 751.

The shared complete event (serving both text and URL paths) uses the request-level `platform` variable:
```python
'meta': {'title': ..., 'creator': ..., 'platform': platform, 'likes': ...}
```

In text mode, `meta["platform"]` is correctly set to `"text"` (line 715), but the complete event reads the outer `platform` variable, which defaults to `"xhs"` (from `body.get("platform", "xhs")` on line 677). The frontend receives `"platform": "xhs"` for a text-only submission.

**Brief expected behavior** (lines 50-51 of the brief):
```python
'meta': {..., 'platform': 'text', 'likes': '0'}
```

**Fix:** Change `'platform': platform` to `'platform': meta.get('platform', platform)` on line 751, so text mode's `meta["platform"] = "text"` takes priority. The URL path's `meta` (from `step_resolve`) typically lacks a `platform` key, so it would fall through to the `platform` default just as before. Verify `step_resolve` does not set a `meta["platform"]` key that would conflict -- if it does, the fallback order should be platform (URL) or meta (text).

```python
# Line 751, change:
'platform': platform,
# to:
'platform': meta.get('platform', platform),
```

---

## 3. Code Quality Assessment

### Positive

- **Shared code path for Step 4.** Merging both branches into one `step_generate` call + one complete event is cleaner than the brief's approach (duplicated Step 4 + complete in both branches). This is an improvement over the spec.
- **Finally block is naturally safe.** No special-case handling needed; `get("audio_path", "")` returns `""` for text-mode tasks, and `os.path.exists("")` is `False`.
- **URL processing path is byte-for-byte unchanged.** The `else` branch contains the original code exactly.
- **Fixup commit correctly addressed the `"skipped"` status issue.** All 3 progress events now emit `"status": "done"`, matching the frontend's allowed set (`running`/`done`/`error`).
- **No new dependencies.** No changes to pipeline functions or external imports.

### Minor nitpicks (not blocking)

1. **Progress message text.** `"Text input mode"` vs the brief's `"skipped"`. The frontend does not display this field visibly (it only checks `status`), so this is harmless. But diverging from spec without reason is a mild practice concern.

2. **Docstring.** `"""Process a video URL or text input: → transcribe → notes."""` -- the first `→` is a stray, and the original `download` step is lost. Suggest: `"""Process a video URL or text input: download → transcribe → notes. SSE for progress."""`

3. **task.url for text mode.** Setting `tasks[task_id]["url"]` to `""` (empty string) when only text is provided. The brief uses `"(text input)"`. The `url` field is exposed via `GET /api/task/{task_id}` and may confuse if a consumer checks truthiness rather than the `meta.platform` field. Low risk in practice since the frontend checks `meta.platform` first.

4. **Inline events vs for-loop.** The brief uses a concise loop:
   ```python
   for step_name in ["resolve", "download", "transcribe"]:
       tasks[task_id]["progress"] = {"step": step_name, "status": "done", "message": "skipped"}
       yield ...
   ```
   The implementation writes each step out individually. This is functionally identical but less maintainable (adding/renaming a step requires updating 3 blocks instead of 1 list element). Recommend refactoring to the loop form if this code is touched again.

---

## 4. Global Constraints Check

| Constraint | Status |
|---|---|
| Don't modify existing link processing flow | PASS -- wrapped in `else:`, original code intact |
| Text mode skips resolve/download/transcribe, generates directly | PASS |
| Progress events use status `"done"` (not `"skipped"`) | PASS -- fixed in 878ad5e |
| Text mode skips audio storage (finally block no-op) | PASS -- `get("audio_path", "")` returns falsy |

---

## 5. Test Coverage Assessment

The report lists 10 manual test cases. All are meaningful. Suggested additions:

- **`platform` = `"xhs"` + text only** -- should return `"platform": "text"` in complete event meta, NOT `"xhs"`. This would have caught Bug 1.
- **No platform param + text only** -- same check.
- **`platform` = `"bilibili"` + text only** -- should still return `"platform": "text"`.
- **Long text input (10k+ chars)** -- ensure no truncation or encoding issues in SSE or `step_generate`.

---

## Summary

The implementation is well-structured and meets all global constraints. The shared-code-path design for Step 4 is an improvement over the brief. One bug (incorrect `platform` in complete event for text mode) must be fixed before release. Four minor cosmetic deviations from the brief are noted but not blocking.

**Action:** Fix Bug 1 (line 751, `'platform': meta.get('platform', platform)`) then merge.
