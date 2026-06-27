# Task 5 Report: JavaScript Logic for Mode Switching, Text Submission, and Download Hiding

## Summary
Added all JavaScript logic to support the dual-mode (URL + Text) input UI built in Tasks 3-4. No existing link-mode logic was changed.

## Changes Made

### File: `static/index.html` (script block only)

### 1. New State Variable
- Added `let currentInputMode = 'url';` to track which input mode is active.

### 2. New Function: `switchMode(mode)`
- Toggles `.active` class between `tabUrl` and `tabText` tab buttons.
- Shows/hides `urlInputGroup` and `textInputGroup` containers.
- Updates submit button text: "开始处理" for URL mode, "生成笔记" for text mode.
- Sets `currentInputMode` state.

### 3. Modified: `handleSubmit()`
- Added text-mode routing at the top: if `currentInputMode === 'text'`, calls `processText()` and returns early.
- All existing URL/search logic below is untouched.

### 4. New Function: `processText()`
- Validates that both title and text inputs are non-empty (shows toast if not).
- Sends POST to `/api/process-text` with `{text, title, mode}` in JSON body.
- Reads SSE stream using the same pattern as `processURL()`.
- Reuses the existing `handleSSEEvent()` for progress/complete/error events.
- Manages submit button disabled state and text.

### 5. Modified: `updateModeHint()`
- Added `scholar` mode hint: "深度详解，适合学习研究".
- Refactored to use a hints lookup object for cleaner code.

### 6. Modified: `showPreview()`
- In text mode: hides download buttons (`.dl-audio`, `.dl-transcript`, `.dl-merged`, `.dl-full`) and transcript preview section.
- In URL mode: shows all download buttons and conditionally shows transcript preview (existing behavior preserved).

### 7. Modified: `resetAll()`
- Clears `titleInput` and `textInput` values.
- Resets transcript preview display and content.
- Resets download button visibility.
- All existing reset logic preserved.

## What Was NOT Changed
- `processURL()` — untouched
- `searchVideos()` — untouched
- `selectResult()`, `backToSearch()` — untouched
- `handleSSEEvent()` — untouched (reused by `processText()`)
- All download/copy action functions — untouched
- All history functions — untouched
- All HTML markup and CSS — untouched

## Bug Fix (2026-06-27)

### 1. Fixed Incorrect API Endpoint in `processText()`
- **File:** `static/index.html` (line 903)
- **Bug:** `processText()` sent POST to `/api/process-text`, which does not exist on the backend. Requests would return 404.
- **Fix:** Changed the fetch URL from `'/api/process-text'` to `'/api/process'`, matching the actual backend route (`@app.post("/api/process")` in `app.py`).
- **Root cause:** A typo in the endpoint name during initial implementation — presumably `process-text` was chosen to match the function name rather than the actual backend route.
