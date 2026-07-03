# Design Language: Linear – The system for product development

> Extracted from `https://linear.app` on July 2, 2026
> 4309 elements analyzed

This document describes the complete design language of the website. It is structured for AI/LLM consumption — use it to faithfully recreate the visual design in any framework.

## Color Palette

### Primary Colors

| Role | Hex | RGB | HSL | Usage Count |
|------|-----|-----|-----|-------------|
| Primary | `#e4f222` | rgb(228, 242, 34) | hsl(64, 89%, 54%) | 2 |
| Secondary | `#5e6ad2` | rgb(94, 106, 210) | hsl(234, 56%, 60%) | 3 |
| Accent | `#00ff05` | rgb(0, 255, 5) | hsl(121, 100%, 50%) | 19 |

### Neutral Colors

| Hex | HSL | Usage Count |
|-----|-----|-------------|
| `#f7f8f8` | hsl(180, 7%, 97%) | 6761 |
| `#62666d` | hsl(218, 5%, 41%) | 749 |
| `#d0d6e0` | hsl(218, 21%, 85%) | 410 |
| `#e2e4e7` | hsl(216, 9%, 90%) | 295 |
| `#8a8f98` | hsl(219, 6%, 57%) | 272 |
| `#08090a` | hsl(210, 11%, 4%) | 53 |
| `#23252a` | hsl(223, 9%, 15%) | 12 |
| `#000000` | hsl(0, 0%, 0%) | 6 |
| `#383b3f` | hsl(214, 6%, 23%) | 5 |
| `#121414` | hsl(180, 5%, 7%) | 4 |
| `#313234` | hsl(220, 3%, 20%) | 2 |
| `#1c1c1d` | hsl(240, 2%, 11%) | 1 |

### Background Colors

Used on large-area elements: `#08090a`, `#090a0b`, `#101112`, `#121314`, `#ffffff`, `#161718`, `#0f1011`, `#e4f222`

### Text Colors

Text color palette: `#f7f8f8`, `#ffffff`, `#8a8f98`, `#08090a`, `#d0d6e0`, `#e2e4e6`, `#62666d`, `#e2e4e7`, `#27a644`, `#f34f52`

### Gradients

```css
background-image: linear-gradient(rgba(11, 11, 11, 0.8) 0%, oklab(0.149576 0.00000680983 0.00000298768 / 0.761905) 100%);
```

```css
background-image: radial-gradient(52.53% 57.5% at 50% 100%, rgba(8, 9, 10, 0) 0%, rgba(8, 9, 10, 0.5) 100%), linear-gradient(rgb(8, 9, 10) 10%, rgb(208, 214, 224) 100%);
```

```css
background-image: radial-gradient(50% 50%, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0) 90%);
```

```css
background-image: radial-gradient(circle, rgba(255, 255, 255, 0.04) 0%, rgba(0, 0, 0, 0) 50%);
```

```css
background-image: linear-gradient(90deg, color(srgb 0 0 0 / 0) 0%, color(srgb 0.6 0.231373 0.231373 / 0.2) 100%), none;
```

```css
background-image: linear-gradient(90deg, color(srgb 0 0 0 / 0) 0%, color(srgb 0.129412 0.701961 1 / 0.2) 100%), none;
```

```css
background-image: radial-gradient(circle, rgba(255, 255, 255, 0.03) 0%, rgba(0, 0, 0, 0) 50%);
```

```css
background-image: repeating-linear-gradient(to right, rgb(35, 37, 42) 0px, rgb(35, 37, 42) 3px, rgba(0, 0, 0, 0) 3px, rgba(0, 0, 0, 0) 7px);
```

```css
background-image: repeating-linear-gradient(rgb(35, 37, 42) 0px, rgb(35, 37, 42) 3px, rgba(0, 0, 0, 0) 3px, rgba(0, 0, 0, 0) 7px);
```

```css
background-image: radial-gradient(circle, rgba(255, 255, 255, 0.02) 0%, rgba(0, 0, 0, 0) 50%);
```

```css
background-image: linear-gradient(0deg, rgba(255, 255, 255, 0.4) 0%, rgba(255, 255, 255, 0.4) 100%), linear-gradient(rgb(178, 213, 255) 0%, rgb(223, 209, 255) 100%);
```

### Full Color Inventory

| Hex | Contexts | Count |
|-----|----------|-------|
| `#f7f8f8` | text, border, background | 6761 |
| `#62666d` | text, border, background | 749 |
| `#d0d6e0` | text, border | 410 |
| `#e2e4e7` | background, border, text | 295 |
| `#8a8f98` | text, border | 272 |
| `#f79ce0` | text, border | 90 |
| `#08090a` | background, text, border | 53 |
| `#f7bf8b` | text, border | 44 |
| `#8fa6ff` | text, border | 32 |
| `#ffdf9f` | text, border | 20 |
| `#83dcdc` | text, border | 20 |
| `#00ff05` | background | 19 |
| `#f34e52` | text, border, background | 14 |
| `#23252a` | background, border | 12 |
| `#27a644` | text, border, background | 11 |
| `#000000` | background | 6 |
| `#ff0000` | background | 6 |
| `#383b3f` | border, background | 5 |
| `#6366f1` | background | 5 |
| `#121414` | background | 4 |
| `#02b8cc` | background | 4 |
| `#5e6ad2` | background | 3 |
| `#8b5cf6` | background | 3 |
| `#55ccff` | background | 3 |
| `#313234` | border | 2 |
| `#6d78d5` | text, border | 2 |
| `#e4f222` | background | 2 |
| `#1c1c1d` | background | 1 |
| `#10b981` | background | 1 |
| `#0f3338` | background | 1 |

## Typography

### Font Families

- **Inter Variable** — used for all (3991 elements)
- **Berkeley Mono** — used for body (318 elements)

### Type Scale

| Size (px) | Size (rem) | Weight | Line Height | Letter Spacing | Used On |
|-----------|------------|--------|-------------|----------------|---------|
| 64px | 4rem | 510 | 64px | -1.408px | h1, span, br |
| 48px | 3rem | 510 | 48px | -1.056px | h2 |
| 40px | 2.5rem | 510 | 44px | -0.88px | h2, strong |
| 32px | 2rem | 400 | 36px | -0.704px | p |
| 24px | 1.5rem | 400 | 31.92px | -0.288px | p, blockquote |
| 20px | 1.25rem | 590 | 26.6px | -0.24px | h3 |
| 18px | 1.125rem | 400 | 28.8px | -0.165px | span |
| 17px | 1.0625rem | 590 | 27.2px | normal | span |
| 16px | 1rem | 400 | normal | normal | html, head, meta, link |
| 15px | 0.9375rem | 400 | 24px | -0.165px | p, span, div, strong |
| 14px | 0.875rem | 510 | 21px | normal | a, span, p, code |
| 13.3333px | 0.8333rem | 400 | normal | normal | button, span, svg, path |
| 13px | 0.8125rem | 400 | 19.5px | normal | button, a, svg, path |
| 12px | 0.75rem | 510 | 16.8px | normal | span, div, img, svg |
| 11px | 0.6875rem | 400 | 15.4px | normal | span |

### Heading Scale

```css
h1 { font-size: 64px; font-weight: 510; line-height: 64px; }
h2 { font-size: 48px; font-weight: 510; line-height: 48px; }
h2 { font-size: 40px; font-weight: 510; line-height: 44px; }
h3 { font-size: 20px; font-weight: 590; line-height: 26.6px; }
h4 { font-size: 16px; font-weight: 400; line-height: normal; }
h3 { font-size: 13px; font-weight: 400; line-height: 19.5px; }
```

### Body Text

```css
body { font-size: 14px; font-weight: 510; line-height: 21px; }
```

### Font Weights in Use

`400` (4046x), `510` (241x), `590` (18x), `300` (4x)

## Spacing

| Token | Value | Rem |
|-------|-------|-----|
| spacing-1 | 1px | 0.0625rem |
| spacing-39 | 39px | 2.4375rem |
| spacing-47 | 47px | 2.9375rem |
| spacing-51 | 51px | 3.1875rem |
| spacing-56 | 56px | 3.5rem |
| spacing-69 | 69px | 4.3125rem |
| spacing-79 | 79px | 4.9375rem |
| spacing-91 | 91px | 5.6875rem |
| spacing-95 | 95px | 5.9375rem |
| spacing-99 | 99px | 6.1875rem |
| spacing-111 | 111px | 6.9375rem |
| spacing-123 | 123px | 7.6875rem |
| spacing-127 | 127px | 7.9375rem |
| spacing-131 | 131px | 8.1875rem |
| spacing-135 | 135px | 8.4375rem |
| spacing-152 | 152px | 9.5rem |
| spacing-155 | 155px | 9.6875rem |
| spacing-159 | 159px | 9.9375rem |
| spacing-166 | 166px | 10.375rem |
| spacing-199 | 199px | 12.4375rem |

## Border Radii

| Label | Value | Count |
|-------|-------|-------|
| xs | 1px | 1 |
| sm | 4px | 38 |
| md | 7px | 2 |
| lg | 12px | 23 |
| lg | 16px | 3 |
| xl | 20px | 2 |
| full | 50px | 38 |
| full | 400px | 1 |
| full | 9999px | 23 |

## Box Shadows

**sm** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0.1) 0px 0px 0px 2px;
```

**sm** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0.2) 0px 0px 0px 1px;
```

**sm (inset)** — blur: 0px
```css
box-shadow: rgb(35, 37, 42) 0px 0px 0px 1px inset;
```

**sm** — blur: 0px
```css
box-shadow: rgba(8, 9, 10, 0.1) 0px 0px 0px 1px, rgba(8, 9, 10, 0.4) 0px 0px 64px 0px;
```

**sm (inset)** — blur: 0px
```css
box-shadow: rgba(255, 255, 255, 0.03) 0px 0px 0px 1px inset, rgba(255, 255, 255, 0.04) 0px 1px 0px 0px inset, rgba(0, 0, 0, 0.6) 0px 0px 0px 1px, rgba(0, 0, 0, 0.1) 0px 4px 4px 0px;
```

**xs** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0.4) 0px 1px 0px 0px;
```

**xs (inset)** — blur: 0px
```css
box-shadow: rgb(35, 37, 42) 1px 0px 0px 0px inset;
```

**xs** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0.03) 0px 1.2px 0px 0px;
```

**sm** — blur: 4px
```css
box-shadow: rgba(0, 0, 0, 0.4) 0px 2px 4px 0px;
```

**md** — blur: 2px
```css
box-shadow: rgba(0, 0, 0, 0) 0px 8px 2px 0px, rgba(0, 0, 0, 0.01) 0px 5px 2px 0px, rgba(0, 0, 0, 0.04) 0px 3px 2px 0px, rgba(0, 0, 0, 0.07) 0px 1px 1px 0px, rgba(0, 0, 0, 0.08) 0px 0px 1px 0px;
```

**md (inset)** — blur: 12px
```css
box-shadow: rgba(0, 0, 0, 0.2) 0px 0px 12px 0px inset;
```

**xl** — blur: 32px
```css
box-shadow: rgba(8, 9, 10, 0.6) 0px 4px 32px 0px;
```

## CSS Custom Properties

### Colors

```css
--color-overlay-dim-rgb: 255, 255, 255;
--color-text-secondary: #d0d6e0;
--color-text-tertiary: #8a8f98;
--icon-replacement-color: ;
--color-line-tertiary: #18191a;
--color-white: #fff;
--color-accent: #7170ff;
--color-border-translucent: #ffffff0d;
--color-selection-bg: color-mix(in lch, #5e6ad2, black 10%);
--color-line-secondary: #202122;
--color-bg-level-3: #191a1b;
--editor-text-color: #e4e5e9;
--color-line-primary: #37393a;
--color-fg-primary: #f7f8f8;
--color-bg-quinary: #282828;
--color-text-quaternary: #62666d;
--color-alpha: 255;
--layer-popover: 600;
--color-border-secondary: #34343a;
--color-accent-tint: #18182f;
--btn-highlight-bg: transparent;
--color-accent-hover: #828fff;
--header-bg: #0b0b0bcc;
--color-line-quaternary: #141515;
--color-black: #000;
--color-border-tertiary: #3e3e44;
--scrollbar-color-hover: #fff3;
--color-link-hover: #fff;
--color-button-invert-bg-hover: #fff;
--icon-default-color: ;
--color-button-invert-bg: #e5e5e6;
--color-bg-level-1: #0f1011;
--color-fg-quaternary: #62666d;
--color-overlay-primary: #000000d9;
--color-brand-text: #fff;
--btn-highlight-color: ;
--color-teal: #00b8cc;
--color-linear-plan: #68cc58;
--color-border-primary: #23252a;
--color-orange: #fc7840;
--color-selection-text: #fff;
--color-fg-secondary: #d0d6e0;
--color-bg-translucent: #ffffff0d;
--color-link-primary: #828fff;
--color-red: #eb5757;
--color-line-tint: #141516;
--color-green: #27a644;
--color-blue: #4ea7fc;
--color-selection-dim: color-mix(in lch, #5e6ad2, transparent 80%);
--color-text-primary: #f7f8f8;
--color-bg-tertiary: #232326;
--color-brand-bg: #5e6ad2;
--focus-ring-outline: 1px solid #5e69d1;
--color-bg-quaternary: #28282c;
--color-bg-marketing: #010102;
--color-bg-panel: #0f1011;
--color-linear-security: #7a7fad;
--color-bg-primary: #08090a;
--focus-ring-offset: 2px;
--color-bg-tint: #141516;
--scrollbar-color-active: #fff6;
--header-border: #ffffff14;
--color-yellow: #f0bf00;
--color-fg-tertiary: #8a8f98;
--focus-ring-width: 1px;
--border-hairline: 1px;
--color-bg-level-0: #08090a;
--color-bg-level-2: #141516;
--scrollbar-color: #ffffff1a;
--focus-ring-color: #5e69d1;
--color-indigo: #5e6ad2;
--icon-color: ;
--color-linear-build: #d4b144;
--color-border-translucent-strong: #ffffff14;
--color-bg-secondary: #1c1c1f;
```

### Spacing

```css
--editor-block-spacing-large: calc(1.375 * 1rem);
--text-micro-size: .75rem;
--font-size-title1: 2.25rem;
--title-3-letter-spacing: -.012em;
--editor-block-menu-size: 20px;
--editor-last-invisible-paragraph-spacing: 10px;
--scrollbar-size-active: 10px;
--text-mini-letter-spacing: -.01em;
--font-size-miniPlus: .75rem;
--text-regular-letter-spacing: -.011em;
--text-regular-size: .9375rem;
--editor-block-spacing-small: calc(.375 * 1rem);
--font-size-microPlus: .6875rem;
--title-7-size: 3.5rem;
--text-tiny-letter-spacing: -.015em;
--text-small-size: .875rem;
--editor-font-size: .9375rem;
--title-2-letter-spacing: -.012em;
--page-padding-block: 64px;
--title-2-size: 1.25rem;
--title-4-size: 2rem;
--editor-letter-spacing: -.00666667em;
--font-size-micro: .6875rem;
--font-size-title2: 1.5rem;
--homepage-outer-padding: 10px;
--title-5-letter-spacing: -.022em;
--font-size-small: .8125rem;
--text-micro-letter-spacing: 0;
--title-6-letter-spacing: -.022em;
--font-size-large: 1.125rem;
--title-9-letter-spacing: -.022em;
--font-size-regularPlus: .9375rem;
--page-padding-right: max(0px, 24px);
--text-mini-size: .8125rem;
--page-padding-left: max(0px, 24px);
--font-monospace: "Berkeley Mono", ui-monospace, "SF Mono", "Menlo", monospace;
--title-6-size: 3rem;
--title-5-size: 2.5rem;
--title-1-letter-spacing: -.012em;
--title-8-size: 4rem;
--scrollbar-size: 6px;
--text-large-size: 1.0625rem;
--min-tap-size: 44px;
--page-padding-inline: 24px;
--title-8-letter-spacing: -.022em;
--text-large-letter-spacing: 0;
--font-size-largePlus: 1.125rem;
--text-small-letter-spacing: -.013em;
--font-size-smallPlus: .8125rem;
--title-9-size: 4.5rem;
--title-7-letter-spacing: -.022em;
--title-3-size: 1.5rem;
--scrollbar-gap: 4px;
--title-1-size: 1.0625rem;
--font-size-title3: 1.25rem;
--editor-block-spacing: 1rem;
--text-tiny-size: .625rem;
--font-size-regular: .9375rem;
--homepage-padding-inset: 32px;
--font-size-mini: .75rem;
--title-4-letter-spacing: -.022em;
--page-padding-y: 48px;
```

### Typography

```css
--text-large-line-height: 1.6;
--title-1-line-height: 1.4;
--font-variations: "opsz" auto;
--font-settings: "cv01", "ss03";
--title-9-line-height: 1;
--font-emoji: "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Segoe UI", "Twemoji Mozilla", "Noto Color Emoji", "Android Emoji";
--text-tiny: .625rem / 1.5 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--text-small-line-height: calc(21 / 14);
--editor-line-height: 1.6;
--font-weight-bold: 680;
--text-large: 1.0625rem / 1.6 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--text-micro: .75rem / 1.4 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--title-2-line-height: 1.33;
--editor-font-weight: 400;
--text-mini: .8125rem / 1.5 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--title-4-line-height: 1.125;
--text-regular: .9375rem / 1.6 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--font-regular: "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--title-3-line-height: 1.33;
--title-6-line-height: 1;
--text-micro-line-height: 1.4;
--text-tiny-line-height: 1.5;
--title-8-line-height: 1.06;
--text-regular-line-height: 1.6;
--text-small: .875rem / calc(21 / 14) "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--font-weight-light: 300;
--font-serif-display: "Tiempos Headline", ui-serif, Georgia, Cambria, "Times New Roman", Times, serif;
--font-weight-semibold: 590;
--title-7-line-height: 1.1;
--title-5-line-height: 1.1;
--layer-context-menu: 1200;
--text-mini-line-height: 1.5;
--font-weight-medium: 510;
--font-weight-normal: 400;
```

### Shadows

```css
--btn-overlay-shadow-hover: none;
--shadow-low: 0px 2px 4px #0000001a;
--shadow-high: 0px 7px 32px #00000059;
--shadow-tiny: 0px 0px 0px transparent;
--btn-overlay-shadow: none;
--shadow-none: 0px 0px 0px transparent;
--shadow-medium: 0px 4px 24px #0003;
--shadow-stack-low: 0px 8px 2px 0px #0000, 0px 5px 2px 0px #00000003, 0px 3px 2px 0px #0000000a, 0px 1px 1px 0px #00000012, 0px 0px 1px 0px #00000014;
```

### Radii

```css
--editor-block-radius: 6px;
--radius-rounded: 9999px;
--radius-circle: 50%;
--radius-8: 8px;
--radius-12: 12px;
--radius-32: 32px;
--rounded-full: 9999px;
--radius-24: 24px;
--radius-4: 4px;
--radius-6: 6px;
--radius-16: 16px;
```

### Other

```css
--sx-ljw4h1: #303236;
--header-height: 72px;
--sx-18pfyxa: 6px 12px;
--editor-todolist-checkbox-width: 14px;
--zoom-in: default;
--sx-1urpf9d: #ffffff0d;
--sx-1stx5uy: #74e3ff;
--sx-7ide1: #747ee9;
--sx-1ijrdvx: #ff8849;
--sx-1uv3w6h: #2c2d32;
--ease-out-quad: cubic-bezier(.25, .46, .45, .94);
--speed-highlightFadeOut: .15s;
--sx-138rywl: 13vh;
--sx-sfnrch: #f0bf00;
--sx-138kmyo: #424449;
--sx-1ltkoa: #626467;
--sx-1mc3c6y: #1e2022;
--sx-1dcvabv: #332024;
--cursor-disabled: not-allowed;
--layer-tooltip: 1100;
--ease-in-out-quart: cubic-bezier(.77, 0, .175, 1);
--sx-91u3ar: #ffcc00;
--sx-18uyzu6: #008a2a;
--sx-ot17o6: #00cee2;
--sx-vatjr0: #34353a;
--sx-1gm0lru: #282a30;
--sx-34xdpc: #d9343f;
--sx-1gxylln: #242629;
--sx-tw6awd: #ffe7de;
--sx-kthb5v: #6c76e0;
--sx-183dfpr: #ff9958;
--ease-in-out-circ: cubic-bezier(.785, .135, .15, .86);
--title-7: 590 3.5rem / 1.1 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--ease-out-quart: cubic-bezier(.165, .84, .44, 1);
--sx-1ccqs4f: #3f4145;
--speed-quickTransition: .1s;
--sx-jw5zf4: #39b350;
--sx-feitbp: #ffffff;
--layer-debug: 5100;
--ease-in-circ: cubic-bezier(.6, .04, .98, .335);
--sx-13sdql6: "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Segoe UI", "Twemoji Mozilla", "Noto Color Emoji", "Android Emoji";
--sx-fwc8so: #cf4608;
--sx-pqiwo2: #373a56;
--title-1: 590 1.0625rem / 1.4 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--transparent: #fff0;
--layer-2: 2;
--sx-1vqca58: #69daff;
--editor-bullet-disc-offset: .5em;
--sx-6zt3z6: 1px solid #323439;
--sx-1fphd1n: #232427;
--ease-in-quart: cubic-bezier(.895, .03, .685, .22);
--ease-in-out-cubic: cubic-bezier(.645, .045, .355, 1);
--sx-5igtf4: #ffffff1b;
--page-inset: 32px;
--sx-1fh23cp: #9c9da1;
--sx-as9fd0: #282a30;
--sx-1vyp3gc: #ffeac6;
--sx-ugsh4: #ffd500;
--ease-in-out-quint: cubic-bezier(.86, 0, .07, 1);
--editor-bullet-disc-width: .5em;
--sx-n8xqcl: #5e69d1;
--sx-1glqxor: #232535;
--sx-w1p5jj: #37393e;
--layer-command-menu: 650;
--ease-in-out-expo: cubic-bezier(1, 0, 0, 1);
--sx-ay0skx: #fefeff;
--sx-1k7v50d: 0 4px 40px #00000019, 0 3px 20px #0000001f,0 3px 12px #0000001f, 0 2px 8px #0000001f, 0 1px 1px #0000001f;
--sx-1ospiv4: #ffffff22;
--sx-or1tl7: #55ccff;
--sx-ys2i3t: #ffffff;
--layer-dialog-overlay: 699;
--sx-umgfby: 0 1px 1px inset #00000011, 0 1px 3px inset #00000011, 0 2px 5px inset #00000019;
--sx-1rzu7x2: #626366;
--layer-footer: 50;
--sx-1jffjrl: #6a76e3;
--sx-cb0zzs: #33353b;
--ease-out-circ: cubic-bezier(.075, .82, .165, 1);
--sx-ch85qk: #5e69d1;
--ease-out-quint: cubic-bezier(.23, 1, .32, 1);
--sx-1n1r1h9: #ffffff0d;
--title-5: 590 2.5rem / 1.1 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--sx-1ubxoo9: #1e2022;
--sx-1cxqmhc: #00e8ff;
--1fr: minmax(0, 1fr);
--sx-5t1vcl: #00ceff;
--sx-2icmlu: #08080826;
--sx-wsz0k3: #26a544;
--sx-cx2ark: #37393e;
--title-6: 590 3rem / 1 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--sx-1qlh175: #00889c;
--dvh: 1dvh;
--sx-193njt9: #ffffff22;
--sx-1h56kua: #f0bf00;
--sx-1rsaf4u: #2a2d48;
--layer-scrollbar: 75;
--sx-35jz1e: #3c3f5c;
--sx-1dhg814: 0 3px 8px #0000001f, 0 2px 5px #0000001f, 0 1px 1px #0000001f;
--100svh: calc(100 * 1svh);
--sx-10lzhmx: 0px 4px 4px -1px #0000000a, 0px 1px 1px 0px #00000014;
--sx-629164: #2c2d30;
--sx-1dd5bcf: #9c9da1;
--sx-1uoekal: #00b8cb;
--sx-k68kma: #37393e;
--cursor-tooltip: help;
--cursor-none: none;
--sx-ykavoc: 8px;
--sx-1uztw8p: #ffffff30;
--scrollbar-width: 12px;
--sx-v3o8qy: #636467;
--mask-visible: black;
--sx-d29rh7: #28292e;
--pointer: default;
--sx-13m9wh7: #007def;
--title-2: 590 1.25rem / 1.33 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--sx-13kjjc4: #38393d;
--sx-1ikf7kw: #ffffff22;
--sx-1q6smeb: #ff6565;
--svh: 1svh;
--sx-c3gk8m: 0 0 0 1px #5e69d1;
--sx-16hn3q3: #292a2e;
--lightningcss-dark: ;
--underline-offset: clamp(2px, .225em, 6px);
--sx-1gakdvt: #25283f;
--ease-in-quint: cubic-bezier(.755, .05, .855, .06);
--speed-highlightFadeIn: 0s;
--sx-1xaoi8i: #7a88ff;
--sx-d1bcc1: #08080826;
--page-max-width: 1024px;
--homepage-max-width: calc(1344px + 10px * 2);
--mask-off: transparent;
--sx-1a798ef: 6px;
--sx-3zwjav: #e4e5e9;
--sx-129bhjt: #967000;
--mask-on: black;
--header-blur: 20px;
--sx-1ipkkxf: "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", "Linear Thai", sans-serif;
--ease-in-quad: cubic-bezier(.55, .085, .68, .53);
--sx-8gevfv: #43bc58;
--title-9: 590 4.5rem / 1 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--layer-overlay: 500;
--sx-180qi0f: #d5ffd6;
--prose-max-width: 624px;
--sx-6od1kq: #dbffff;
--sx-irmyh9: #ffffff13;
--sx-11lpf43: 0.8125rem;
--layer-header: 100;
--grid-columns: 12;
--sx-ws85c5: #fcfaff;
--sx-1bu05id: #ff8583;
--sx-1qdowq0: #00000066;
--sx-6ayg1n: #2c2e34;
--sx-15wwovl: #28292e;
--sx-ikq9iy: #322122;
--sx-19hxmp1: #adbaff;
--layer-max: 10000;
--sx-1o1lnwn: #323439;
--sx-1fj52yw: ;
--layer-toasts: 800;
--sx-1gcjx5j: #2d2f37;
--ease-out-expo: cubic-bezier(.19, 1, .22, 1);
--sx-g52i5g: #1c1f24;
--sx-9o00jb: #00c6d9;
--sx-1em7oyp: #1b263a;
--sx-11vg3qk: #ff7235;
--mask-invisible: transparent;
--sx-i20l48: #f34e52;
--layer-dialog: 700;
--sx-1edn6di: #33353a;
--sx-j1ai0m: #e4e5e9;
--sx-1k7nh0l: #fffaa6;
--editor-block-menu-offset: 28px;
--sx-ickszr: #fefeff;
--speed-regularTransition: .25s;
--sx-1hz3utq: #ff8042;
--layer-3: 3;
--ease-out-cubic: cubic-bezier(.215, .61, .355, 1);
--title-8: 590 4rem / 1.06 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--sx-142jeir: #323439;
--sx-10845vo: #c9ffff;
--sx-axo4ug: 0 0 0 0.5px #323439;
--cursor-pointer: pointer;
--sx-10o0rs5: #e4e5e9;
--editor-safe-area: 16px;
--ease-in-out-quad: cubic-bezier(.455, .03, .515, .955);
--icon-grayscale-image-filter: grayscale(100%) brightness(400%);
--sx-1ps2i54: #1b282d;
--sx-1yxqotz: #5e6ad2;
--layer-skip-nav: 5000;
--sx-1umwnkk: "Berkeley Mono", "SFMono Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
--sx-1jmjcvw: #ffffff1b;
--sx-105wzx7: #edbf0a;
--lightningcss-light: ;
--ease-in-expo: cubic-bezier(.95, .05, .795, .035);
--sx-1uu732i: 12px;
--sx-msgncm: #292521;
--ease-in-cubic: cubic-bezier(.55, .055, .675, .19);
--layer-1: 1;
--sx-hfmm6c: #2d2e31;
--title-4: 590 2rem / 1.125 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--underline-thickness: from-font;
--sx-17ckey5: #ff5d5e;
--sx-74qs5: #00000001;
--sx-1eapsa9: #626366;
--mask-ease: #0003;
--sx-14ggo8w: #1e2823;
--editor-list-inset: 1.5rem;
--title-3: 590 1.5rem / 1.33 "Inter Variable", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", sans-serif;
--sx-1ele6il: 1px;
--sx-7jk47a: #2c2d32;
--100dvh: calc(100 * 1dvh);
--sx-x8afrf: 6px;
--sx-1m4y240: #19191b;
--sx-ciqj87: #3de261;
--sx-bpgheo: #636fd7;
--sx-ds2y8i: 5px;
```

### Semantic

```css
success: [object Object];
warning: [object Object];
error: [object Object];
info: [object Object];
```

## Breakpoints

| Name | Value | Type |
|------|-------|------|
| sm | 600px | max-width |
| sm | 640px | max-width |
| sm | 641px | min-width |
| md | 768px | max-width |
| md | 769px | min-width |
| 928px | 928px | max-width |
| lg | 1024px | max-width |
| lg | 1025px | min-width |
| 1140px | 1140px | max-width |
| xl | 1240px | max-width |
| xl | 1280px | max-width |
| xl | 1281px | min-width |
| 1420px | 1420px | max-width |
| 1440px | 1440px | max-width |
| 2xl | 1536px | min-width |

## Transitions & Animations

**Easing functions:** `[object Object]`, `[object Object]`

**Durations:** `0.1s`, `0.16s`, `0.2s`, `0.4s`

### Common Transitions

```css
transition: all;
transition: border-color 0.1s cubic-bezier(0.25, 0.46, 0.45, 0.94), background 0.1s cubic-bezier(0.25, 0.46, 0.45, 0.94);
transition: color 0.1s cubic-bezier(0.25, 0.46, 0.45, 0.94), background 0.1s cubic-bezier(0.25, 0.46, 0.45, 0.94);
transition: border 0.16s cubic-bezier(0.25, 0.46, 0.45, 0.94), background-color 0.16s cubic-bezier(0.25, 0.46, 0.45, 0.94), color 0.16s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.16s cubic-bezier(0.25, 0.46, 0.45, 0.94), opacity 0.16s cubic-bezier(0.25, 0.46, 0.45, 0.94), filter 0.16s cubic-bezier(0.25, 0.46, 0.45, 0.94), transform 0.16s cubic-bezier(0.25, 0.46, 0.45, 0.94);
transition: 0.16s cubic-bezier(0.25, 0.46, 0.45, 0.94);
transition: filter 0.16s cubic-bezier(0.25, 0.46, 0.45, 0.94);
transition: background 0.16s cubic-bezier(0.25, 0.46, 0.45, 0.94);
transition: fill;
transition: color;
transition: transform 0.16s cubic-bezier(0.25, 0.46, 0.45, 0.94);
```

### Keyframe Animations

**grid-dot-0-0-upDown**
```css
@keyframes grid-dot-0-0-upDown {
  0% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  35.7143% { opacity: 0.3; }
  35.7143% { opacity: 0.3; }
  42.8571% { opacity: 0.3; }
  42.8571% { opacity: 0.3; }
  50% { opacity: 0.3; }
  50% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  64.2857% { opacity: 0.3; }
  64.2857% { opacity: 0.3; }
  71.4286% { opacity: 0.3; }
  71.4286% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  100% { opacity: 0.3; }
}
```

**grid-dot-0-1-upDown**
```css
@keyframes grid-dot-0-1-upDown {
  0% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  35.7143% { opacity: 0.3; }
  35.7143% { opacity: 1; }
  42.8571% { opacity: 1; }
  42.8571% { opacity: 0.3; }
  50% { opacity: 0.3; }
  50% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  57.1429% { opacity: 1; }
  64.2857% { opacity: 1; }
  64.2857% { opacity: 0.3; }
  71.4286% { opacity: 0.3; }
  71.4286% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  100% { opacity: 0.3; }
}
```

**grid-dot-0-2-upDown**
```css
@keyframes grid-dot-0-2-upDown {
  0% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  28.5714% { opacity: 1; }
  35.7143% { opacity: 1; }
  35.7143% { opacity: 1; }
  42.8571% { opacity: 1; }
  42.8571% { opacity: 1; }
  50% { opacity: 1; }
  50% { opacity: 1; }
  57.1429% { opacity: 1; }
  57.1429% { opacity: 1; }
  64.2857% { opacity: 1; }
  64.2857% { opacity: 1; }
  71.4286% { opacity: 1; }
  71.4286% { opacity: 1; }
  78.5714% { opacity: 1; }
  78.5714% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  100% { opacity: 0.3; }
}
```

**grid-dot-0-3-upDown**
```css
@keyframes grid-dot-0-3-upDown {
  0% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  35.7143% { opacity: 0.3; }
  35.7143% { opacity: 1; }
  42.8571% { opacity: 1; }
  42.8571% { opacity: 0.3; }
  50% { opacity: 0.3; }
  50% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  57.1429% { opacity: 1; }
  64.2857% { opacity: 1; }
  64.2857% { opacity: 0.3; }
  71.4286% { opacity: 0.3; }
  71.4286% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  100% { opacity: 0.3; }
}
```

**grid-dot-0-4-upDown**
```css
@keyframes grid-dot-0-4-upDown {
  0% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  35.7143% { opacity: 0.3; }
  35.7143% { opacity: 0.3; }
  42.8571% { opacity: 0.3; }
  42.8571% { opacity: 0.3; }
  50% { opacity: 0.3; }
  50% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  64.2857% { opacity: 0.3; }
  64.2857% { opacity: 0.3; }
  71.4286% { opacity: 0.3; }
  71.4286% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  100% { opacity: 0.3; }
}
```

**grid-dot-1-0-upDown**
```css
@keyframes grid-dot-1-0-upDown {
  0% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  35.7143% { opacity: 0.3; }
  35.7143% { opacity: 0.3; }
  42.8571% { opacity: 0.3; }
  42.8571% { opacity: 0.3; }
  50% { opacity: 0.3; }
  50% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  64.2857% { opacity: 0.3; }
  64.2857% { opacity: 0.3; }
  71.4286% { opacity: 0.3; }
  71.4286% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  100% { opacity: 0.3; }
}
```

**grid-dot-1-1-upDown**
```css
@keyframes grid-dot-1-1-upDown {
  0% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  28.5714% { opacity: 1; }
  35.7143% { opacity: 1; }
  35.7143% { opacity: 0.3; }
  42.8571% { opacity: 0.3; }
  42.8571% { opacity: 0.3; }
  50% { opacity: 0.3; }
  50% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  64.2857% { opacity: 0.3; }
  64.2857% { opacity: 1; }
  71.4286% { opacity: 1; }
  71.4286% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  100% { opacity: 0.3; }
}
```

**grid-dot-1-2-upDown**
```css
@keyframes grid-dot-1-2-upDown {
  0% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  21.4286% { opacity: 1; }
  28.5714% { opacity: 1; }
  28.5714% { opacity: 1; }
  35.7143% { opacity: 1; }
  35.7143% { opacity: 1; }
  42.8571% { opacity: 1; }
  42.8571% { opacity: 1; }
  50% { opacity: 1; }
  50% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  57.1429% { opacity: 1; }
  64.2857% { opacity: 1; }
  64.2857% { opacity: 1; }
  71.4286% { opacity: 1; }
  71.4286% { opacity: 1; }
  78.5714% { opacity: 1; }
  78.5714% { opacity: 1; }
  85.7143% { opacity: 1; }
  85.7143% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  100% { opacity: 0.3; }
}
```

**grid-dot-1-3-upDown**
```css
@keyframes grid-dot-1-3-upDown {
  0% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  28.5714% { opacity: 1; }
  35.7143% { opacity: 1; }
  35.7143% { opacity: 0.3; }
  42.8571% { opacity: 0.3; }
  42.8571% { opacity: 0.3; }
  50% { opacity: 0.3; }
  50% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  64.2857% { opacity: 0.3; }
  64.2857% { opacity: 1; }
  71.4286% { opacity: 1; }
  71.4286% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  100% { opacity: 0.3; }
}
```

**grid-dot-1-4-upDown**
```css
@keyframes grid-dot-1-4-upDown {
  0% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  7.14286% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  14.2857% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  21.4286% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  28.5714% { opacity: 0.3; }
  35.7143% { opacity: 0.3; }
  35.7143% { opacity: 0.3; }
  42.8571% { opacity: 0.3; }
  42.8571% { opacity: 0.3; }
  50% { opacity: 0.3; }
  50% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  57.1429% { opacity: 0.3; }
  64.2857% { opacity: 0.3; }
  64.2857% { opacity: 0.3; }
  71.4286% { opacity: 0.3; }
  71.4286% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  78.5714% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  85.7143% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  92.8571% { opacity: 0.3; }
  100% { opacity: 0.3; }
}
```

## Component Patterns

Detected UI component patterns and their most common styles:

### Buttons (94 instances)

```css
.button {
  background-color: rgba(255, 255, 255, 0.05);
  color: rgb(98, 102, 109);
  font-size: 13.3333px;
  font-weight: 400;
  padding-top: 0px;
  padding-right: 0px;
  border-radius: 0px;
}
```

### Cards (40 instances)

```css
.card {
  background-color: rgba(255, 255, 255, 0.02);
  border-radius: 6px;
  box-shadow: rgba(0, 0, 0, 0.4) 0px 2px 4px 0px;
  padding-top: 8px;
  padding-right: 8px;
}
```

### Inputs (5 instances)

```css
.input {
  background-color: rgb(59, 59, 59);
  color: rgb(255, 255, 255);
  border-color: rgb(255, 255, 255);
  border-radius: 0px;
  font-size: 13.3333px;
  padding-top: 0px;
  padding-right: 32px;
}
```

### Links (76 instances)

```css
.link {
  color: rgb(138, 143, 152);
  font-size: 13px;
  font-weight: 400;
}
```

### Navigation (52 instances)

```css
.navigatio {
  background-color: rgb(35, 37, 42);
  color: rgb(247, 248, 248);
  padding-top: 0px;
  padding-bottom: 0px;
  padding-left: 0px;
  padding-right: 0px;
  position: static;
  box-shadow: rgba(0, 0, 0, 0.4) 0px 1px 0px 0px;
}
```

### Footer (11 instances)

```css
.foote {
  background-color: rgb(8, 9, 10);
  color: rgb(247, 248, 248);
  padding-top: 0px;
  padding-bottom: 0px;
  font-size: 16px;
}
```

### Dropdowns (7 instances)

```css
.dropdown {
  background-color: rgb(23, 23, 24);
  border-radius: 0px;
  border-color: rgb(247, 248, 248);
  padding-top: 0px;
}
```

### Badges (22 instances)

```css
.badge {
  background-color: rgba(255, 255, 255, 0.05);
  color: rgb(247, 248, 248);
  font-size: 10px;
  font-weight: 510;
  padding-top: 0px;
  padding-right: 8px;
  border-radius: 2px;
}
```

### Avatars (4 instances)

```css
.avatar {
  border-radius: 6px;
}
```

### Switches (2 instances)

```css
.switche {
  border-radius: 4px;
  border-color: rgb(255, 255, 255);
}
```

## Component Clusters

Reusable component instances grouped by DOM structure and style similarity:

### Button — 2 instances, 1 variant

**Variant 1** (2 instances)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(138, 143, 152);
  padding: 0px 12px 0px 12px;
  border-radius: 9999px;
  border: 0px none rgb(138, 143, 152);
  font-size: 13px;
  font-weight: 400;
```

### Button — 1 instance, 1 variant

**Variant 1** (1 instance)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(247, 248, 248);
  padding: 0px 0px 0px 0px;
  border-radius: 0px;
  border: 0px none rgb(247, 248, 248);
  font-size: 16px;
  font-weight: 400;
```

### Button — 1 instance, 1 variant

**Variant 1** (1 instance)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(247, 248, 248);
  padding: 0px 0px 0px 0px;
  border-radius: 0px;
  border: 0px none rgb(247, 248, 248);
  font-size: 16px;
  font-weight: 400;
```

### Button — 1 instance, 1 variant

**Variant 1** (1 instance)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(247, 248, 248);
  padding: 0px 0px 0px 0px;
  border-radius: 0px;
  border: 0px none rgb(247, 248, 248);
  font-size: 16px;
  font-weight: 400;
```

### Button — 1 instance, 1 variant

**Variant 1** (1 instance)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(255, 255, 255);
  padding: 0px 4px 0px 4px;
  border-radius: 4px;
  border: 0px none rgb(255, 255, 255);
  font-size: 13.3333px;
  font-weight: 400;
```

### Button — 52 instances, 5 variants

**Variant 1** (4 instances)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(98, 102, 109);
  padding: 0px 0px 0px 0px;
  border-radius: 9999px;
  border: 0px none rgb(98, 102, 109);
  font-size: 13.3333px;
  font-weight: 400;
```

**Variant 2** (20 instances)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(98, 102, 109);
  padding: 0px 6px 0px 4px;
  border-radius: 6px;
  border: 0px none rgb(98, 102, 109);
  font-size: 13px;
  font-weight: 510;
```

**Variant 3** (10 instances)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(255, 255, 255);
  padding: 0px 0px 0px 0px;
  border-radius: 0px;
  border: 0px none rgb(255, 255, 255);
  font-size: 13.3333px;
  font-weight: 400;
```

**Variant 4** (2 instances)

```css
  background: rgba(255, 255, 255, 0.03);
  color: rgb(247, 248, 248);
  padding: 0px 0px 0px 0px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 13.3333px;
  font-weight: 400;
```

**Variant 5** (16 instances)

```css
  background: rgba(255, 255, 255, 0.05);
  color: rgb(98, 102, 109);
  padding: 0px 0px 0px 0px;
  border-radius: 2px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 13.3333px;
  font-weight: 400;
```

### Button — 11 instances, 2 variants

**Variant 1** (10 instances)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(208, 214, 224);
  padding: 0px 6px 0px 6px;
  border-radius: 6px;
  border: 0px none rgb(208, 214, 224);
  font-size: 13px;
  font-weight: 510;
```

**Variant 2** (1 instance)

```css
  background: rgba(255, 255, 255, 0.04);
  color: rgb(208, 214, 224);
  padding: 0px 6px 0px 6px;
  border-radius: 6px;
  border: 0px none rgb(208, 214, 224);
  font-size: 13px;
  font-weight: 510;
```

### Input — 2 instances, 2 variants

**Variant 1** (1 instance)

```css
  background: rgba(255, 255, 255, 0.02);
  color: rgb(208, 214, 224);
  padding: 12px 14px 12px 14px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 13.3333px;
  font-weight: 400;
```

**Variant 2** (1 instance)

```css
  background: rgba(0, 0, 0, 0);
  color: rgba(0, 0, 0, 0);
  padding: 0px 32px 0px 55.8px;
  border-radius: 0px;
  border: 0px none rgba(0, 0, 0, 0);
  font-size: 14px;
  font-weight: 400;
```

### Button — 4 instances, 2 variants

**Variant 1** (2 instances)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(208, 214, 224);
  padding: 0px 10px 0px 5px;
  border-radius: 9999px;
  border: 1px solid rgb(35, 37, 42);
  font-size: 12px;
  font-weight: 510;
```

**Variant 2** (2 instances)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(255, 255, 255);
  padding: 0px 0px 0px 0px;
  border-radius: 0px;
  border: 0px none rgb(255, 255, 255);
  font-size: 13.3333px;
  font-weight: 400;
```

### Button — 16 instances, 1 variant

**Variant 1** (16 instances)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(255, 255, 255);
  padding: 0px 0px 0px 0px;
  border-radius: 0px;
  border: 0px none rgb(255, 255, 255);
  font-size: 13.3333px;
  font-weight: 400;
```

### Input — 1 instance, 1 variant

**Variant 1** (1 instance)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(247, 248, 248);
  padding: 1px 32px 1px 32px;
  border-radius: 0px;
  border: 0px 0px 1px none none solid rgb(247, 248, 248) rgb(247, 248, 248) rgba(255, 255, 255, 0.08);
  font-size: 16px;
  font-weight: 400;
```

### Button — 2 instances, 1 variant

**Variant 1** (2 instances)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(98, 102, 109);
  padding: 0px 12px 0px 12px;
  border-radius: 9999px;
  border: 0px none rgb(98, 102, 109);
  font-size: 13px;
  font-weight: 510;
```

### Button — 2 instances, 1 variant

**Variant 1** (2 instances)

```css
  background: rgb(229, 229, 230);
  color: rgb(8, 9, 10);
  padding: 0px 20px 0px 20px;
  border-radius: 9999px;
  border: 1px solid rgb(229, 229, 230);
  font-size: 16px;
  font-weight: 510;
```

## Layout System

**101 grid containers** and **506 flex containers** detected.

### Container Widths

| Max Width | Padding |
|-----------|---------|
| 1364px | 10px |
| 100% | 0px |
| 1160px | 8px |
| 1250px | 32px |
| 480px | 0px |
| 560px | 0px |
| 520px | 24px |

### Grid Column Patterns

| Columns | Usage Count |
|---------|-------------|
| 1-column | 75x |
| 2-column | 17x |
| 3-column | 2x |
| 12-column | 1x |
| 6-column | 1x |

### Grid Templates

```css
grid-template-columns: 1280px;
grid-template-columns: 232px 952px;
grid-template-columns: 638px 638px;
gap: 16px;
grid-template-columns: 670px 280px;
grid-template-columns: 210px 210px 210px 210px 210px 210px;
```

### Flex Patterns

| Direction/Wrap | Count |
|----------------|-------|
| row/nowrap | 401x |
| column/nowrap | 105x |

**Gap values:** `12px`, `15px`, `16px`, `20px`, `24px`, `2px`, `32px`, `3px`, `40px`, `4px`, `5px`, `64px`, `6px`, `8px`

## Responsive Design

### Viewport Snapshots

| Viewport | Body Font | Nav Visible | Max Columns | Hamburger | Page Height |
|----------|-----------|-------------|-------------|-----------|-------------|
| mobile (375px) | 16px | Yes | 5 | Yes | 6358px |
| tablet (768px) | 16px | Yes | 5 | Yes | 9772px |
| desktop (1280px) | 16px | Yes | 2 | Yes | 10511px |
| wide (1920px) | 16px | Yes | 2 | Yes | 10962px |

### Breakpoint Changes

**375px → 768px** (mobile → tablet):
- H1 size: `38px` → `56px`
- Page height: `6358px` → `9772px`

**768px → 1280px** (tablet → desktop):
- H1 size: `56px` → `64px`
- Max grid columns: `5` → `2`
- Page height: `9772px` → `10511px`

**1280px → 1920px** (desktop → wide):
- Page height: `10511px` → `10962px`

## Interaction States

### Button States

**"Product"**
```css
/* Hover */
color: rgb(138, 143, 152) → rgb(243, 244, 245);
background-color: rgba(0, 0, 0, 0) → rgba(255, 255, 255, 0.07);
border-color: rgb(138, 143, 152) → rgb(243, 244, 245);
```
```css
/* Focus */
color: rgb(138, 143, 152) → rgb(247, 248, 248);
background-color: rgba(0, 0, 0, 0) → rgba(255, 255, 255, 0.08);
border-color: rgb(138, 143, 152) → rgb(247, 248, 248);
outline: rgba(0, 0, 0, 0) none 3px → rgb(94, 105, 209) solid 1px;
```

**"Resources"**
```css
/* Hover */
color: rgb(138, 143, 152) → rgb(243, 244, 245);
background-color: rgba(0, 0, 0, 0) → rgba(255, 255, 255, 0.075);
border-color: rgb(138, 143, 152) → rgb(243, 244, 245);
```
```css
/* Focus */
color: rgb(138, 143, 152) → rgb(247, 248, 248);
background-color: rgba(0, 0, 0, 0) → rgba(255, 255, 255, 0.08);
border-color: rgb(138, 143, 152) → rgb(247, 248, 248);
outline: rgba(0, 0, 0, 0) none 3px → rgb(94, 105, 209) solid 1px;
```

**"Linear"**
```css
/* Hover */
background-color: rgba(0, 0, 0, 0) → rgba(255, 255, 255, 0.027);
```
```css
/* Focus */
background-color: rgba(0, 0, 0, 0) → rgba(255, 255, 255, 0.03);
outline: rgba(0, 0, 0, 0) none 3px → rgb(94, 105, 209) solid 1px;
```

### Link Hover

```css
color: rgb(138, 143, 152) → rgb(247, 248, 248);
background-color: rgba(0, 0, 0, 0) → rgba(255, 255, 255, 0.08);
border-color: rgb(138, 143, 152) → rgb(247, 248, 248);
```

### Input Focus

```css
outline: rgba(0, 0, 0, 0) none 3px → rgb(94, 105, 209) solid 1px;
```

## Accessibility (WCAG 2.1)

**Overall Score: 83%** — 5 passing, 1 failing color pairs

### Failing Color Pairs

| Foreground | Background | Ratio | Level | Used On |
|------------|------------|-------|-------|---------|
| `#6d78d5` | `#232534` | 3.82:1 | FAIL | span (1x) |

### Passing Color Pairs

| Foreground | Background | Ratio | Level |
|------------|------------|-------|-------|
| `#08090a` | `#e5e5e6` | 15.83:1 | AAA |
| `#ffffff` | `#5e6ad2` | 4.7:1 | AA |

## Design System Score

**Overall: 76/100 (Grade: C)**

| Category | Score |
|----------|-------|
| Color Discipline | 80/100 |
| Typography Consistency | 82/100 |
| Spacing System | 70/100 |
| Shadow Consistency | 78/100 |
| Border Radius Consistency | 80/100 |
| Accessibility | 83/100 |
| CSS Tokenization | 100/100 |

**Strengths:** Good CSS variable tokenization

**Issues:**
- 1 WCAG contrast failures
- 131 !important rules — prefer specificity over overrides
- 78% of CSS is unused — consider purging
- 12469 duplicate CSS declarations

## Gradients

**13 unique gradients** detected.

| Type | Direction | Stops | Classification |
|------|-----------|-------|----------------|
| linear | — | 2 | brand |
| radial | — | 3 | bold |
| linear | — | 2 | brand |
| radial | — | 3 | bold |
| radial | circle | 2 | brand |
| linear | 90deg | 2 | brand |
| linear | 90deg | 2 | brand |
| radial | circle | 2 | brand |
| repeating-linear | to right | 4 | bold |
| repeating-linear | — | 4 | bold |
| radial | circle | 2 | brand |
| linear | 0deg | 2 | brand |
| linear | — | 2 | brand |

```css
background: linear-gradient(rgba(11, 11, 11, 0.8) 0%, oklab(0.149576 0.00000680983 0.00000298768 / 0.761905) 100%);
background: radial-gradient(52.53% 57.5% at 50% 100%, rgba(8, 9, 10, 0) 0%, rgba(8, 9, 10, 0.5) 100%);
background: linear-gradient(rgb(8, 9, 10) 10%, rgb(208, 214, 224) 100%);
background: radial-gradient(50% 50%, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0) 90%);
background: radial-gradient(circle, rgba(255, 255, 255, 0.04) 0%, rgba(0, 0, 0, 0) 50%);
```

## Z-Index Map

**7 unique z-index values** across 4 layers.

| Layer | Range | Elements |
|-------|-------|----------|
| modal | 5000,9999999 | a.L.S.q.k.9.q._.r.o.o.t, div.T.Z.T.s.Q.G._.v.i.e.w.p.o.r.t.P.o.s.i.t.i.o.n. .h.i.d.e.-.m.o.b.i.l.e, div.s.c.-.j.H.b.x.o.U. .h.t.g.I.L.S |
| dropdown | 100,100 | header.T.Z.T.s.Q.G._.h.e.a.d.e.r |
| sticky | 50,50 | footer.J.m.h.1.W.q._.f.o.o.t.e.r |
| base | 1,3 | div.w.9.Z.F.k.q._.c.h.a.t.B.o.x, header.p.w.x.C.z.W._.h.e.a.d.e.r, div.M.w.J.d.i.W._.g.l.o.w |

**Issues:**
- [object Object]

## SVG Icons

**94 unique SVG icons** detected. Dominant style: **filled**.

| Size Class | Count |
|------------|-------|
| xs | 36 |
| sm | 35 |
| md | 10 |
| xl | 13 |

**Icon colors:** `currentColor`, `#E2E4E6`, `var(--label-faint)`, `#9c9da1`, `var(--color-yellow)`, `rgb(0, 0, 0)`, `var(--color-text-tertiary)`, `var(--color-teal)`, `var(--color-red)`, `var(--color-text-quaternary)`

## Font Files

| Family | Source | Weights | Styles |
|--------|--------|---------|--------|
| Inter Variable | self-hosted | 100 900 | normal, italic |
| Berkeley Mono | self-hosted | 100 900 | normal |
| Tiempos Headline | self-hosted | 400 | normal |

## Image Style Patterns

| Pattern | Count | Key Styles |
|---------|-------|------------|
| thumbnail | 92 | objectFit: fill, borderRadius: 0px, shape: square |
| avatar | 21 | objectFit: cover, borderRadius: 50%, shape: circular |
| gallery | 4 | objectFit: fill, borderRadius: 0px, shape: square |

**Aspect ratios:** 1:1 (114x), 16:9 (2x), 2.15:1 (1x)

## Motion Language

**Feel:** responsive · **Scroll-linked:** yes

### Duration Tokens

| name | value | ms |
|---|---|---|
| `xs` | `100ms` | 100 |
| `sm` | `160ms` | 160 |
| `md` | `400ms` | 400 |

### Easing Families

- **ease-out** (83 uses) — `cubic-bezier(0.25, 0.46, 0.45, 0.94)`
- **ease-in-out** (25 uses) — `ease`

### Keyframes In Use

| name | kind | properties | uses |
|---|---|---|---|
| `grid-dot-0-0-upDown` | fade | opacity | 2 |
| `grid-dot-0-1-upDown` | fade | opacity | 2 |
| `grid-dot-0-2-upDown` | fade | opacity | 2 |
| `grid-dot-0-3-upDown` | fade | opacity | 2 |
| `grid-dot-0-4-upDown` | fade | opacity | 2 |
| `grid-dot-1-0-upDown` | fade | opacity | 2 |
| `grid-dot-1-1-upDown` | fade | opacity | 2 |
| `grid-dot-1-2-upDown` | fade | opacity | 2 |
| `grid-dot-1-3-upDown` | fade | opacity | 2 |
| `grid-dot-1-4-upDown` | fade | opacity | 2 |
| `grid-dot-2-0-upDown` | fade | opacity | 2 |
| `grid-dot-2-1-upDown` | fade | opacity | 2 |
| `grid-dot-2-2-upDown` | fade | opacity | 2 |
| `grid-dot-2-3-upDown` | fade | opacity | 2 |
| `grid-dot-2-4-upDown` | fade | opacity | 2 |
| `grid-dot-3-0-upDown` | fade | opacity | 2 |
| `grid-dot-3-1-upDown` | fade | opacity | 2 |
| `grid-dot-3-2-upDown` | fade | opacity | 2 |
| `grid-dot-3-3-upDown` | fade | opacity | 2 |
| `grid-dot-3-4-upDown` | fade | opacity | 2 |

## Component Anatomy

### button — 93 instances

**Slots:** label
**Variants:** ghost · secondary
**Sizes:** small · large

| variant | count | sample label |
|---|---|---|
| default | 88 | Product |
| ghost | 3 | Linear |
| secondary | 2 | Listen |

### input — 3 instances


## Brand Voice

**Tone:** neutral · **Pronoun:** you-only · **Headings:** Sentence case (balanced)

### Top CTA Verbs

- **linear** (5)
- **sign** (2)
- **pulse** (2)
- **initiatives** (2)
- **projects** (2)
- **agents** (2)
- **product** (1)
- **resources** (1)

### Button Copy Patterns

- "linear" (2×)
- "product" (1×)
- "resources" (1×)
- "log in
sign up" (1×)
- "log in" (1×)
- "sign up" (1×)
- "inbox" (1×)
- "my issues" (1×)
- "reviews" (1×)
- "pulse" (1×)

### Sample Headings

> The product development
system for teams and agents
The product development system for teams and agents
> Faster app launch
> A new species of product tool. Purpose-built for modern teams with AI workflows at its core, Linear sets a new standard for planning and building products.
> Make product operations self-driving
> Define the product direction
> Make product operations self-driving
> Define the product direction
> Move work forward across teams and agents
> Review PRs and agent output
> Understand progress at scale

## Page Intent

**Type:** `landing` (confidence 0.31)
**Description:** Purpose-built for planning and building products with AI agents.

Alternates: blog-post (0.35)

## Section Roles

Reading order (top→bottom): content → testimonials → logo-wall → nav → nav → nav → nav → content → testimonials → nav → testimonials → nav → hero → nav → testimonial → hero → nav → nav → nav → testimonial → cta → footer

| # | Role | Heading | Confidence |
|---|------|---------|------------|
| 0 | content | — | 0.3 |
| 1 | logo-wall | — | 0.85 |
| 2 | nav | — | 0.9 |
| 3 | testimonials | The product development
system for teams and agents
The product development syst | 0.4 |
| 4 | nav | — | 0.9 |
| 5 | nav | — | 0.4 |
| 6 | nav | — | 0.4 |
| 7 | content | — | 0.3 |
| 8 | testimonials | Make product operations self-driving | 0.4 |
| 9 | nav | — | 0.4 |
| 10 | testimonials | Define the product direction | 0.4 |
| 11 | nav | — | 0.4 |
| 12 | hero | Move work forward across teams and agents | 0.4 |
| 13 | nav | — | 0.4 |
| 14 | testimonial | Review PRs and agent output | 0.8 |
| 15 | hero | Understand progress at scale | 0.4 |
| 16 | nav | — | 0.4 |
| 17 | nav | — | 0.4 |
| 18 | nav | — | 0.4 |
| 19 | testimonial | — | 0.8 |

## Material Language

**Label:** `material-you` (confidence 0.45)

| Metric | Value |
|--------|-------|
| Avg saturation | 0.444 |
| Shadow profile | soft |
| Avg shadow blur | 0px |
| Max radius | 9999px |
| backdrop-filter in use | no |
| Gradients | 13 |

## Imagery Style

**Label:** `mixed` (confidence 0.017)
**Counts:** total 117, svg 89, icon 111, screenshot-like 0, photo-like 0
**Dominant aspect:** square-ish
**Radius profile on images:** soft

## Component Screenshots

12 retina crops written to `screenshots/`. Index: `*-screenshots.json`.

| Cluster | Variant | Size (px) | File |
|---------|---------|-----------|------|
| button--default | 0 | 72 × 32 | `screenshots/button-default-0.png` |
| button--default | 1 | 89 × 32 | `screenshots/button-default-1.png` |
| button--default | 2 | 143 × 32 | `screenshots/button-default-2.png` |
| input--default | 0 | 374 × 68 | `screenshots/input-default-0.png` |
| input--default | 1 | 558 × 64 | `screenshots/input-default-1.png` |
| input--default | 2 | 621 × 432 | `screenshots/input-default-2.png` |
| button--ghost | 0 | 24 × 24 | `screenshots/button-ghost-0.png` |
| button--ghost--small | 0 | 83 × 32 | `screenshots/button-ghost-small-0.png` |
| button--ghost--small | 1 | 68 × 32 | `screenshots/button-ghost-small-1.png` |
| button--secondary--small | 0 | 85 × 32 | `screenshots/button-secondary-small-0.png` |
| button--default--large | 0 | 127 × 44 | `screenshots/button-default-large-0.png` |
| button--secondary--large | 0 | 144 × 44 | `screenshots/button-secondary-large-0.png` |

Full-page: `screenshots/full-page.png`

## Quick Start

To recreate this design in a new project:

1. **Install fonts:** Add `Inter Variable` from Google Fonts or your font provider
2. **Import CSS variables:** Copy `variables.css` into your project
3. **Tailwind users:** Use the generated `tailwind.config.js` to extend your theme
4. **Design tokens:** Import `design-tokens.json` for tooling integration
