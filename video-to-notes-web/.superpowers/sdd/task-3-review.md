# Task 3 Review: CSS for Input Tabs, Textarea, Title Input, Mode Buttons

## Verdict: PASS with 2 minor issues

The CSS additions are well-crafted, reuse project variables consistently, and match the existing visual language. Two issues noted below.

---

## What was reviewed

Commit `f2601d3` added 100 lines of CSS to `static/index.html` for:
- `.input-tabs` / `.input-tab` — horizontal tab bar
- `.input-textarea` — vertically resizable textarea
- `.title-input` — full-width title input
- `.mode-btn-group` / `.mode-btn` — button-style mode selector
- Mobile overrides for all of the above

---

## What checks passed

1. **CSS variables reused** — All colors, fonts, and radii pull from `:root` custom properties (`--bg`, `--surface`, `--border`, `--text`, `--text-dim`, `--heading`, `--accent`, `--font`, `--radius`, `--radius-sm`). No hardcoded color values except in the focus box-shadow (which matches the existing pattern at line 88).

2. **Focus styles consistent** — `.input-textarea:focus`, `.title-input:focus`, and `.input-tab` all use the same `border-color: var(--accent)` + `box-shadow: 0 0 0 3px rgba(139,115,85,0.08)` pattern as `.input-row input:focus` (line 88).

3. **Textarea matches input style** — Same `background: var(--surface)`, `border: 1px solid var(--border)`, `border-radius: var(--radius)`, `outline: none`, and placeholder color as `.input-row input`.

4. **Tab buttons visually distinct from action buttons** — `.input-tab` uses `background: none; border: none; border-bottom` underline style, which is the correct pattern for tabs (not trying to look like `.btn`).

5. **Mobile overrides present** — All four new component groups have `@media (max-width: 600px)` overrides with reduced font sizes and padding.

6. **No global style changes** — Diff confirms additions only, no modifications to existing selectors.

7. **Selector specificity ordering** — `.mode-btn.active` appears after `.mode-btn:hover`, so the active state wins on hover (correct behavior).

---

## Issues found

### Issue 1 (Medium): `.mode-btn-group` and `.mode-btn` are unused dead CSS

The HTML body (lines 498-502) still uses the existing `.mode-select` pattern with radio buttons:

```html
<div class="mode-select">
  <label><input type="radio" name="mode" value="standard" checked>...</label>
  <label><input type="radio" name="mode" value="detailed">...</label>
</div>
```

There are zero HTML elements with class `mode-btn-group` or `mode-btn`. The 24 lines of CSS for these classes (lines 179-205, plus the mobile override at line 463) will never apply to any rendered element.

This is dead code in the stylesheet. Either:
- Remove the `.mode-btn-group` / `.mode-btn` CSS (and its mobile override) if the plan stays with radio buttons, OR
- Add corresponding HTML elements and wire up JS to toggle the `.active` class, if the intent is to switch to button-style mode selection

### Issue 2 (Low): `.title-input` padding differs slightly from `.input-row input`

- `.input-row input`: `padding: 12px 16px`
- `.title-input`: `padding: 10px 16px`

This is a 2px difference in vertical padding. It is minor and could be intentional (titles often benefit from slightly tighter padding), but the task brief said "textarea 与 input 同风格." If strict visual consistency is desired, this should be `padding: 12px 16px`.

---

## Class naming note (non-issue)

The plan referenced `.text-input-area` and `.text-title-input`, but the implementer used `.input-textarea` and `.title-input`. The implementer's names are actually **more consistent** with the existing file:

- `.input-textarea` aligns with the `input-` prefix pattern already used by `.input-card` and `.input-row`
- `.title-input` is simpler and avoids introducing a `text-` prefix not used anywhere else

No action needed.

---

## Recommendation

Address Issue 1 (dead CSS) before merging. Either remove the `.mode-btn*` rules or commit to using them in the HTML. Issue 2 is optional.
