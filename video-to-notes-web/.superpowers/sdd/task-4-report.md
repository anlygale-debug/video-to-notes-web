# Task 4 Report: Frontend — HTML additions

## Summary

Added HTML for input tabs, text mode fields, and scholar radio button to `static/index.html`.

## Changes Made

**File: `/Users/yubo/Claude code test/video-to-notes-web/static/index.html`**

### 1. Replaced `.input-card` div (lines 488-522)

- Added `.input-tabs` with two buttons: "链接" (active by default) and "文本"
- Wrapped the existing URL input and platform select in a `#urlInputGroup` div (still visible by default)
- Added `#textInputGroup` (hidden by default) with:
  - `<input>` using class `.title-input` (existing CSS class, renamed from plan's `.text-title-input`)
  - `<textarea>` using class `.input-textarea` (existing CSS class, renamed from plan's `.text-input-area`)
- Added third radio button `value="scholar"` labeled "详解笔记" to the existing `.mode-select` layout

### 2. Added download button classes (lines 560-563)

- `.dl-audio` on the audio download button
- `.dl-transcript` on the transcript download button
- `.dl-merged` on the merged download button
- `.dl-full` on the full package download button

These classes will be used by JS (Task 5) to hide them in text mode.

## Verification

- Confirmed via `git diff` that changes are correct
- Used existing CSS class names (`.input-textarea`, `.title-input`) as specified in the task brief
- Mode-select radio button layout preserved as-is, just one new radio added
- Committed as `445d084` with message: "feat: add input tabs, text mode fields, scholar radio button"
