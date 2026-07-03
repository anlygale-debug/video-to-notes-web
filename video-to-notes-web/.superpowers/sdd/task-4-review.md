# Task 4 Review: Frontend — HTML additions

## Verdict: PASS

All constraints and check items are satisfied. No blocking issues.

---

## Constraint Verification

### 1. All changes in original index.html
**PASS.** The diff (`f2601d3..445d084`) shows changes only in `static/index.html`. No other files were modified.

### 2. Text mode fields use correct Task 3 CSS classes
**PASS.** All four CSS classes are correctly applied and exist in the stylesheet:

| Class | Usage (line) | CSS definition (line) |
|---|---|---|
| `.input-tabs` | 490 | 112 |
| `.input-tab` | 491-492 | 118 |
| `.title-input` | 509 | 159 |
| `.input-textarea` | 510 | 138 |

### 3. Download buttons have correct class markers
**PASS.** All four classes are present:

| Button | Class | Line |
|---|---|---|
| Audio download | `.dl-audio` | 563 |
| Transcript download | `.dl-transcript` | 564 |
| Merged download | `.dl-merged` | 565 |
| Full package download | `.dl-full` | 566 |

### 4. Existing link input functionality preserved
**PASS.** The original `#urlInput` and `#platformSelect` are unchanged inside the new `#urlInputGroup` wrapper. The wrapper has no `display:none`, so URL input remains visible by default.

### 5. Mode-select retains radio button layout, only third radio added
**PASS.** The existing two radio buttons (`standard` and `detailed`) are intact, with one new `<label>` for `scholar` appended. The `onchange="updateModeHint()"` handler is consistently applied to all three.

---

## Check Item Verification

### HTML element IDs for Task 5 JS
**PASS.** All six required IDs are present and correctly named:

| ID | Element | Line |
|---|---|---|
| `urlInputGroup` | `<div>` wrapper for URL input | 496 |
| `textInputGroup` | `<div>` wrapper for text mode | 508 |
| `titleInput` | `<input>` for title | 509 |
| `textInput` | `<textarea>` for transcript text | 510 |
| `tabUrl` | `<button>` for URL tab | 491 |
| `tabText` | `<button>` for Text tab | 492 |

### Scholar radio button value
**PASS.** `value="scholar"` on line 516. Label text is "详解笔记".

### Download button classes for show/hide logic
**PASS.** Each of the four download buttons has its dedicated class for Task 5 JS to target in show/hide toggling.

---

## Minor Observations (non-blocking)

1. **`display:none` is inline rather than a CSS class.** The `#textInputGroup` uses `style="display:none"` (line 508). A dedicated `.hidden` class would be slightly cleaner, but inline style is functionally equivalent and Task 5 JS can toggle it just as easily.

2. **`switchMode()` is not yet defined.** The tab buttons call `switchMode('url')` and `switchMode('text')` via `onclick`. This is expected — Task 5 is responsible for implementing this JS function. No issue for this task's scope.

3. **Scholar mode hint not yet wired.** The `updateModeHint()` handler exists on all three radios, but the hint text for `scholar` mode will need to be added in JS (Task 5). This is outside the scope of Task 4.

---

## Summary

The HTML diff is minimal, precise, and exactly matches the Task 4 brief requirements. All elements have the correct IDs and classes needed by Task 5. No regressions to existing functionality. Ready for Task 5 integration.
