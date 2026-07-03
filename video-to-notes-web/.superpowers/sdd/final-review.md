# Final Branch Review: Text Input + Scholar Mode

**Branch range:** `a4b0f9d..be69e35` (9 commits)
**Review date:** 2026-06-27
**Result:** APPROVE with 1 HIGH and 5 MEDIUM findings

---

## Summary

The branch adds two features to the Video to Notes web app:

1. **Text input mode** -- users paste transcript text directly instead of providing a video URL. The backend skips download/transcription and feeds the text to the LLM. Frontend adds tab-based URL/text switching, hides audio/transcript download buttons in text mode.

2. **Scholar mode** -- a third note generation style producing detailed narrative notes with adaptive chunking (single pass for <=8000 chars, chunk+summarize for longer). Available in both URL and text input modes.

Architecture: changes are scoped to `app.py` and `static/index.html` only. The URL processing path is wrapped in an `else` branch and is structurally unmodified. No new Python dependencies were added.

---

## Finding Summary

| ID | Severity | Area | Title |
|----|----------|------|-------|
| F1 | HIGH | Security | XSS via unsanitized `marked.parse()` rendering LLM output |
| F2 | MEDIUM | Security | No input length limit in backend for text mode |
| F3 | MEDIUM | Code Quality | Duplicate chunking logic in `_generate_detailed` and `_generate_scholar` |
| F4 | MEDIUM | Robustness | Silent chunk failures produce content gaps |
| F5 | MEDIUM | Pre-existing | `HTTPException` used without import (NameError on error paths) |
| F6 | LOW | Integration | `currentInputMode` not reset on `resetAll()` |

---

## F1 [HIGH] -- XSS via unsanitized `marked.parse()` rendering LLM output

**File:** `static/index.html`, line 944
**Code:**
```js
$previewContent.innerHTML = marked.parse(md);
```

**Problem:** The `marked` library (v5+) has no built-in HTML sanitizer. LLM-generated markdown is rendered verbatim as innerHTML. In text input mode, user-provided content flows through the LLM prompt and could be echoed back with embedded `<script>`, `<img onerror>`, or other executable HTML within the markdown output. In URL mode, a malicious video transcript could trigger the same.

**Risk:** An attacker could craft input that, after LLM processing, produces markdown containing executable JavaScript. When the victim views the rendered preview, the script executes in the origin of the Video to Notes app. While self-XSS is the primary scenario (the attacker is also the victim for text input), shared history links or exported files could extend the blast radius.

**Fix:** Wrap the output with a sanitizer:
```js
// Option A: Use DOMPurify (add CDN script tag)
$previewContent.innerHTML = DOMPurify.sanitize(marked.parse(md));

// Option B: If on marked <5, use the built-in sanitizer
$previewContent.innerHTML = marked.parse(md, {sanitize: true});
```
Recommend Option A (DOMPurify) since marked dropped built-in sanitization.

**Urgency:** Fix before any public deployment. For personal single-user use, self-XSS risk is lower but still present if importing others' transcripts.

---

## F2 [MEDIUM] -- No input length limit in backend for text mode

**File:** `app.py`, line 711 (`transcript = text`)
**Problem:** The backend assigns the full `text` body to `transcript` with no length validation. The spec says "后端不做限制" intentionally, but this means a user could POST multi-megabyte text bodies, which would then be embedded in LLM prompts. The LLM call would fail on token limits, but only after the full body has been buffered in memory and passed through string operations.

**Risk:** Memory exhaustion or excessive API costs if very large text is submitted. The frontend has no client-side truncation either (the spec mentions a 50000-char truncation hint but it was not implemented).

**Fix:** Add a reasonable server-side cap (e.g., 100,000 characters) with a clear error response:
```python
if len(text) > 100000:
    return JSONResponse({"error": "text too long (max 100,000 chars)"}, status_code=400)
```
And implement the frontend truncation warning at 50,000 characters as specified in the design doc.

---

## F3 [MEDIUM] -- Duplicate chunking logic

**Files:** `app.py` lines 418-425 (`_generate_detailed`) and lines 550-558 (`_generate_scholar`)

**Problem:** Both functions contain nearly identical chunking code:
```python
chunk_size = 6000
overlap = 300
chunks = []
start = 0
while start < len(transcript):
    end = min(start + chunk_size, len(transcript))
    chunks.append(transcript[start:end])
    start = end - overlap if end < len(transcript) else end
```

**Risk:** If chunk size or overlap strategy changes, both functions must be updated. Inconsistent updates would cause divergent behavior between detailed and scholar modes.

**Fix:** Extract a shared helper:
```python
def _chunk_text(text, chunk_size=6000, overlap=300):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start = end - overlap if end < len(text) else end
    return chunks
```

---

## F4 [MEDIUM] -- Silent chunk failures produce content gaps

**Files:** `app.py` lines 439-451 (`_generate_detailed`) and lines 571-581 (`_generate_scholar`)

**Problem:** Both chunked processing functions initialize `chunk_notes = [""] * total` and later filter with `chunk_notes = [n for n in chunk_notes if n]`. When individual chunks fail (LLM returns None), their positions become empty strings, which are filtered out. The remaining chunks are concatenated in order, but the content corresponding to failed chunks is silently lost with no error indication to the user.

**Risk:** For long content processed in scholar mode, the user receives incomplete notes with no warning that sections were dropped. The "overview" and "terminology table" generated by the summary pass would also be based on incomplete information.

**Fix:** Track per-chunk success and surface warnings:
```python
failed_indices = [i for i, n in enumerate(chunk_notes) if not n]
if failed_indices:
    tasks[task_id]["notes"] = (notes or "") + f"\n\n> Warning: sections {failed_indices} failed to process."
```
At minimum, log the failure so it can be diagnosed.

---

## F5 [MEDIUM] -- `HTTPException` used without import (PRE-EXISTING)

**File:** `app.py` lines 775, 821, 832, 845, 860, 878
**Code:**
```python
from fastapi import FastAPI, Request   # line 8 -- no HTTPException

# line 775:
raise HTTPException(400, "No notes content")
# line 821:
raise HTTPException(404, "Audio not found")
# ... and 4 more occurrences in download endpoints
```

**Problem:** `HTTPException` is used in `export_pdf` and all download endpoints but is never imported. This would raise `NameError` at runtime whenever these error paths are triggered.

**Verification:**
```
AST analysis confirms: HTTPException used=True, imported from fastapi=False
```

**Risk:** Any request hitting these error paths (e.g., downloading audio for a task where transcription failed, exporting PDF with empty notes) will crash with a 500 Internal Server Error instead of returning a proper 4xx response. The successful paths work fine because HTTPException is never raised.

**Fix:** Add `HTTPException` to the FastAPI import:
```python
from fastapi import FastAPI, Request, HTTPException
```

**Note:** This is pre-existing, not introduced in this branch, but was discovered during review. The branch's text-mode changes do not make this worse -- text mode cannot reach the audio/transcript download endpoints (buttons are hidden), but `export_pdf` is still reachable.

---

## F6 [LOW] -- `currentInputMode` not reset on `resetAll()`

**File:** `static/index.html`, `resetAll()` function (lines 1017-1029)

**Problem:** The `resetAll()` function clears input fields, preview, progress, and download button visibility, but does not reset `currentInputMode` to `'url'`. If a user is in text mode and clicks "reset", the download buttons are restored (via the explicit selector reset on line 1027), but `currentInputMode` remains `'text'`. This means:
- `handleSubmit()` will still route to `processText()` if Enter is pressed
- `showPreview()` will still apply text-mode download button hiding for the next result

This is a state inconsistency that persists across a reset.

**Fix:** Add `currentInputMode = 'url';` to `resetAll()` and optionally switch the tabs back:
```js
currentInputMode = 'url';
switchMode('url');  // or manually reset tab classes
```

---

## Regression Analysis

### URL processing -- NO REGRESSION

The `/api/process` endpoint wraps the original URL flow in an `else` branch:
```python
if text:
    # new text path
else:
    # original URL path (structurally unchanged)
```
The validation changed from `if not url` to `if not url and not text`, which is backward-compatible: when only `url` is provided (old behavior), the check passes identically.

One intentional change was `'platform': meta.get('platform', platform)` replacing `'platform': platform` in the complete event payload. This was a bug fix (text mode was incorrectly reporting platform "xhs"), and for URL mode `meta.get('platform', platform)` resolves to the same value as before (`platform` from the request body), so no regression.

### step_generate routing -- NO REGRESSION

The scholar check is added before the detailed check:
```python
if mode == "scholar":
    return _generate_scholar(...)
elif mode == "detailed" and len(transcript) > 4000:
    return _generate_detailed(...)
else:
    return _generate_standard(...)
```
Modes are mutually exclusive strings. When `mode="standard"` or `mode="detailed"`, neither the new `scholar` branch nor the behavior of `detailed`/`standard` is affected.

### Frontend URL mode -- NO REGRESSION

The tab system defaults to URL mode (`tabUrl` has class `active`, `urlInputGroup` is visible, `textInputGroup` has `display:none`). The mode radio defaults to "standard" (unchanged). All existing URL-mode UI, search, processing, download, and history flows are preserved.

---

## Integration Observations

1. **SSE event flow is clean:** Both `processURL()` and `processText()` reuse the same `handleSSEEvent()` function, which was not modified. Text-mode progress events use `status: "done"` (fixed from the earlier `"skipped"` value), which `handleSSEEvent` correctly recognizes.

2. **Download button visibility is correct:** The `showPreview()` function hides audio/transcript/merged/full download buttons in text mode, and `resetAll()` restores them. The integration is consistent.

3. **History entries correctly reflect input source:** Text-mode history entries show `platform: "text"` (fixed from the earlier bug that reported "xhs"), and URL-mode entries show the correct platform. History rendering uses the platform value for the badge.

4. **Meta title override works for both modes:** The `override_title` parameter from the search result selection serves double duty naturally -- it fills `meta["title"]` in URL mode and becomes the title in text mode.

---

## Design vs. Implementation Gap

| Spec requirement | Status |
|---|---|
| Text input with title (required) | IMPLEMENTED |
| Tab切换 (链接/文本) | IMPLEMENTED |
| Text mode hides 平台选择 and 搜索 | IMPLEMENTED |
| Scholar mode radio button | IMPLEMENTED |
| Scholar single pass for <=8000 chars | IMPLEMENTED |
| Scholar chunk+summarize for >8000 chars | IMPLEMENTED |
| Summary pass: overview + terms + takeaway | IMPLEMENTED |
| Scholar available in URL mode too | IMPLEMENTED |
| Text mode hides audio/transcript download buttons | IMPLEMENTED |
| 前段50000字符截断提示 | **NOT IMPLEMENTED** -- spec mentions this but neither frontend nor backend enforces it |
| Text mode submit button says "生成笔记" | IMPLEMENTED |
| Prompt uses > blockquotes for exact phrases | IMPLEMENTED |
| Output in Chinese | IMPLEMENTED (prompt instruction) |

---

## Commits Reviewed

```
be69e35 fix: reset currentInputUrl in processText() to prevent URL leakage into text-mode history
703a2d3 fix: correct API endpoint in processText() from /api/process-text to /api/process
8e8f5cd feat: add JS logic for mode switching, text submission, and download hiding
445d084 feat: add input tabs, text mode fields, scholar radio button
f2601d3 Add CSS for input tabs, textarea, title input, and mode buttons
b076ddd fix: use meta.platform instead of request body platform in complete event
878ad5e fix: change skipped status to done in text-mode progress events, fix default creator and title
3e88360 feat: add text input support to /api/process endpoint
f37a835 feat: add scholar mode with adaptive chunking for reading-based notes
```

All fixes identified in per-task reviews (Task 2 and Task 5 reports) are present in the final branch. The commit history is clean and each commit is atomic.

---

## Recommendation

**APPROVE** with the following actions before merge:

1. **[Required]** Fix F1 (XSS) by adding DOMPurify or configuring marked sanitization
2. **[Recommended]** Fix F5 (HTTPException import) since you are touching the import line anyway -- this is a one-line change
3. **[Nice-to-have]** Extract shared chunking helper (F3)
4. **[Nice-to-have]** Add failed-chunk warnings (F4)
5. **[Nice-to-have]** Implement the 50000-char frontend truncation warning described in the spec
