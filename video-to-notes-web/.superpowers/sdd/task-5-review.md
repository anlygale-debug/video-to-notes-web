# Task 5 Review: JavaScript Logic for Mode Switching, Text Submission, and Download Hiding

## Verdicts

| Criterion | Verdict |
|-----------|---------|
| Spec Compliance | PASS (1 noted deviation) |
| Task Quality | Approved (1 bug, 2 minors) |

---

## 1. Spec Compliance Check

### Global Constraints

| # | Constraint | Status | Evidence |
|---|-----------|--------|----------|
| 1 | processURL untouched | PASS | Lines 799-844 identical |
| 2 | searchVideos untouched | PASS | Lines 731-769 identical |
| 3 | selectResult untouched | PASS | Lines 771-779 identical |
| 4 | backToSearch untouched | PASS | Lines 781-796 identical |
| 5 | handleSSEEvent untouched | PASS | Lines 846-876 identical |
| 6 | processText() calls /api/process | PASS | Line 903: `fetch('/api/process',...)` (was initially `/api/process-text`, fixed in commit 703a2d3) |
| 7 | processText() body is {text, title, mode} | PASS | Line 906: `JSON.stringify({text, title, mode})` |
| 8 | updateModeHint() supports scholar | PASS | Line 703: `scholar: '深度详解，适合学习研究'` |
| 9 | showPreview() hides download buttons + transcript in text mode | PASS | Lines 947-958: conditional hide/show by mode |
| 10 | resetAll() clears titleInput and textInput | PASS | Lines 1018-1019 |
| 11 | switchMode() toggles tabs and input groups | PASS | Lines 708-728 |

### Spec Brief Step-by-Step

| Step | Requirement | Status | Notes |
|------|------------|--------|-------|
| 1 | State var + switchMode() | PASS | `currentInputMode = 'url'` added; switchMode toggles tabs/groups/button text |
| 2 | handleSubmit() routes text mode | PASS | Text mode check at line 680-683, early return |
| 3 | processText() with SSE stream | PASS | Validation, fetch, SSE reader, handleSSEEvent reuse |
| 4 | updateModeHint() for 3 modes | PASS | Scholar hint wording differs from spec but is functionally equivalent |
| 5 | showPreview() hides text-inapplicable items | PASS | DLL buttons hidden, transcript preview hidden in text mode |
| 6 | resetAll() clears text fields | PASS | titleInput, textInput, transcriptContent, transcriptPreview all cleared |
| 7 | Commit | PASS | Two commits: feat + fix |

---

## 2. Code Quality Findings

### Bug 1: `currentInputUrl` not cleared in `processText()` (MEDIUM)

**Location:** `static/index.html`, function `processText()` (lines 879-931)

**Problem:** The spec (task-5-brief.md, Step 3, line 74) explicitly includes `currentInputUrl = '';` inside `processText()`. This line is missing from the implementation.

**Impact:** If a user previously processed a URL (e.g., YouTube), then switches to text mode and processes text, the old URL leaks into the history record. In `handleSSEEvent()` (line 862), `currentMeta.url = currentInputUrl;` — the complete event handler blindly copies `currentInputUrl` into the metadata, then the history save at line 869 stores `url: currentInputUrl`. This means text-mode notes get incorrectly associated with a prior URL-mode video.

**Fix:** Add `currentInputUrl = '';` inside `processText()`, after the validation check and before the fetch call. The canonical location per spec is right after hiding preview:
```javascript
$preview.style.display = 'none';
currentInputUrl = '';  // <-- add this line
```

### Minor 1: Validation message is less specific than spec

**Location:** Line 882-884

**Spec has:**
```javascript
if (!text) { showToast('请粘贴文本内容'); return; }
if (!title) { showToast('请输入标题'); return; }
```

**Actual has:**
```javascript
if (!title || !text) {
  showToast('请输入标题和文本内容');
  return;
}
```

The combined check with a single message doesn't tell the user which field they missed. If the user fills in the title but forgets the text, they see a message implying both are missing. This is a minor UX friction point.

### Minor 2: Scholar hint wording differs from spec

**Spec says:** `scholar: '逐段详解，替代看视频学习'`
**Actual:** `scholar: '深度详解，适合学习研究'`

Both communicate the scholar mode's purpose. The actual wording is arguably clearer for the Chinese audience. Not a functional concern, just noted for completeness.

### Observation: Error event routing in text mode

When `handleSSEEvent` receives an `error` event (line 873-875), it always marks `stepResolve` as error. In text mode, `stepResolve` is in `pending` state (never set to `running`), while `stepGenerate` was the active step. This creates a minor UX mismatch — the error appears on the wrong step in the progress UI. However, this is a consequence of reusing `handleSSEEvent` unchanged per the global constraint, so it is not a new issue introduced by this task.

---

## 3. What Was Done Well

- **Clean separation:** The text-mode routing in `handleSubmit()` is a single 3-line block at the top with early return. All existing URL/search logic remains completely untouched below it. This is the least invasive approach possible.
- **SSE stream reuse:** `processText()` correctly reuses the same `handleSSEEvent()` callback and the same SSE parsing pattern as `processURL()`, avoiding code duplication.
- **Bug follow-up:** The API endpoint bug (`/api/process-text` -> `/api/process`) was caught and fixed in a follow-up commit (703a2d3), demonstrating good discipline.
- **resetAll() completeness:** The reset function properly restores download button visibility via inline style clearing (`b.style.display = ''`) so that subsequent URL-mode previews will show all buttons.
- **Mode state in showPreview():** The conditional logic correctly separates text-mode behavior (hide downloads and transcript) from URL-mode behavior (show all, conditionally show transcript).

---

## 4. Summary

The implementation correctly delivers all six spec requirements and all seven global constraints. One spec line (`currentInputUrl = ''`) was missed in `processText()`, causing a medium-severity bug where old URLs leak into text-mode history entries. Two minor deviations from the spec (validation message style, scholar hint wording) are cosmetic and do not affect functionality. The API endpoint fix commit shows good post-implementation review.

**Recommended action before merge:** Add `currentInputUrl = '';` to `processText()`.
