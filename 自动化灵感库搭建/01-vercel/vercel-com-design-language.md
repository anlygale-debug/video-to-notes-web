# Design Language: Agentic Infrastructure - Vercel

> Extracted from `https://vercel.com` on July 2, 2026
> 1186 elements analyzed

This document describes the complete design language of the website. It is structured for AI/LLM consumption — use it to faithfully recreate the visual design in any framework.

## Color Palette

### Primary Colors

| Role | Hex | RGB | HSL | Usage Count |
|------|-----|-----|-----|-------------|
| Primary | `#0070f3` | rgb(0, 112, 243) | hsl(212, 100%, 48%) | 3 |

### Neutral Colors

| Hex | HSL | Usage Count |
|-----|-----|-------------|
| `#ebebeb` | hsl(0, 0%, 92%) | 1174 |
| `#171717` | hsl(0, 0%, 9%) | 866 |
| `#4d4d4d` | hsl(0, 0%, 30%) | 210 |
| `#666666` | hsl(0, 0%, 40%) | 79 |
| `#ffffff` | hsl(0, 0%, 100%) | 40 |
| `#8f8f8f` | hsl(0, 0%, 56%) | 22 |
| `#a8a8a8` | hsl(0, 0%, 66%) | 7 |
| `#000000` | hsl(0, 0%, 0%) | 4 |
| `#7d7d7d` | hsl(0, 0%, 49%) | 3 |
| `#383838` | hsl(0, 0%, 22%) | 1 |

### Background Colors

Used on large-area elements: `#fafafa`, `#f4f4f4`, `#171717`, `#ffffff`

### Text Colors

Text color palette: `#171717`, `#0072f5`, `#000000`, `#4d4d4d`, `#ffffff`, `#8f8f8f`, `#7d7d7d`, `#a8a8a8`, `#666666`, `#0070f3`

### Gradients

```css
background-image: linear-gradient(to top in oklab, rgb(250, 250, 250) 0%, rgba(0, 0, 0, 0) 100%);
```

```css
background-image: radial-gradient(circle at 0% 0%, rgb(250, 250, 250) 0%, rgba(0, 0, 0, 0) 30%), radial-gradient(circle at 100% 0%, rgb(250, 250, 250) 0%, rgba(0, 0, 0, 0) 30%), radial-gradient(circle at 100% 100%, rgb(250, 250, 250) 0%, rgba(0, 0, 0, 0) 30%);
```

```css
background-image: linear-gradient(to top, rgb(250, 250, 250) 0%, oklab(0 0 0 / 0) 100%);
```

```css
background-image: linear-gradient(to right, rgb(250, 250, 250) 0%, oklab(0 0 0 / 0) 100%);
```

```css
background-image: linear-gradient(to right in oklab, rgba(0, 0, 0, 0) 0%, rgb(255, 255, 255) 100%);
```

### Full Color Inventory

| Hex | Contexts | Count |
|-----|----------|-------|
| `#ebebeb` | border, background | 1174 |
| `#171717` | text, background, border | 866 |
| `#4d4d4d` | text | 210 |
| `#666666` | text | 79 |
| `#ffffff` | background, text | 40 |
| `#8f8f8f` | text | 22 |
| `#a8a8a8` | text | 7 |
| `#000000` | text, border | 4 |
| `#0070f3` | text, background | 3 |
| `#7d7d7d` | text | 3 |
| `#383838` | background | 1 |

## Typography

### Font Families

- **GeistSans** — used for all (1114 elements)
- **Geist Mono** — used for all (72 elements)

### Type Scale

| Size (px) | Size (rem) | Weight | Line Height | Letter Spacing | Used On |
|-----------|------------|--------|-------------|----------------|---------|
| 64px | 4rem | 400 | 64px | -3.84px | h1 |
| 56px | 3.5rem | 450 | 56px | -3.36px | h2 |
| 30px | 1.875rem | 400 | 33px | -1.5px | p, span |
| 24px | 1.5rem | 400 | 32px | normal | summary, svg, path, a |
| 22px | 1.375rem | 400 | 28px | -0.66px | span, svg, path |
| 20px | 1.25rem | 400 | 28px | normal | a, svg, path |
| 16px | 1rem | 400 | 24px | normal | html, head, style, meta |
| 14px | 0.875rem | 400 | 20px | normal | button, span, svg, g |
| 13px | 0.8125rem | 600 | 13px | -0.13px | span |
| 12px | 0.75rem | 400 | 16px | 0.6px | h3, p |
| 8px | 0.5rem | 600 | 8px | normal | span |

### Heading Scale

```css
h1 { font-size: 64px; font-weight: 400; line-height: 64px; }
h2 { font-size: 56px; font-weight: 450; line-height: 56px; }
h5 { font-size: 14px; font-weight: 400; line-height: 20px; }
h3 { font-size: 12px; font-weight: 400; line-height: 16px; }
```

### Body Text

```css
body { font-size: 14px; font-weight: 400; line-height: 20px; }
```

### Font Weights in Use

`400` (1118x), `500` (37x), `600` (26x), `450` (5x)

## Spacing

**Base unit:** 4px

| Token | Value | Rem |
|-------|-------|-----|
| spacing-1 | 1px | 0.0625rem |
| spacing-32 | 32px | 2rem |
| spacing-40 | 40px | 2.5rem |
| spacing-64 | 64px | 4rem |
| spacing-80 | 80px | 5rem |
| spacing-208 | 208px | 13rem |
| spacing-256 | 256px | 16rem |
| spacing-276 | 276px | 17.25rem |

## Border Radii

| Label | Value | Count |
|-------|-------|-------|
| xs | 2px | 9 |
| md | 6px | 59 |
| lg | 12px | 1 |

## Box Shadows

**sm** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgb(255, 255, 255) 0px 0px 0px 2px, rgb(0, 114, 245) 0px 0px 0px 4px;
```

**sm** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.08) 0px 1px 0px 0px;
```

**sm** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.04) 0px 2px 2px 0px, rgba(0, 0, 0, 0.04) 0px 8px 16px -4px;
```

**sm** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.1) 0px 1px 0px 0px;
```

**sm** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgb(235, 235, 235) 0px 0px 0px 1px;
```

**sm (inset)** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.08) 0px 0px 0px 1px inset;
```

**sm** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.08) 0px 0px 0px 1px, rgb(250, 250, 250) 0px 0px 0px 1px;
```

**sm** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0.08) 0px 0px 0px 1px, rgba(0, 0, 0, 0.04) 0px 2px 2px 0px, rgb(250, 250, 250) 0px 0px 0px 1px;
```

**sm** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0.08) 0px 0px 0px 1px, rgba(0, 0, 0, 0.02) 0px 1px 1px 0px, rgba(0, 0, 0, 0.04) 0px 4px 8px -4px, rgba(0, 0, 0, 0.06) 0px 16px 24px -8px, rgb(250, 250, 250) 0px 0px 0px 1px;
```

**sm** — blur: 0px
```css
box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.08) 0px 0px 0px 1px, rgba(0, 0, 0, 0.02) 0px 1px 1px 0px, rgba(0, 0, 0, 0.04) 0px 4px 8px 0px, rgb(250, 250, 250) 0px 0px 0px 1px, rgb(255, 255, 255) 0px 0px 0px 1px;
```

## CSS Custom Properties

### Colors

```css
--ds-shadow-border-large: 0 0 0 1px #00000014, 0px 2px 2px #0000000a, 0px 8px 16px -4px #0000000a, 0 0 0 1px hsla(0, 0%, 98%, 1);
--ds-focus-ring-outline: 2px solid hsla(212, 100%, 48%, 1);
--geist-console-text-color-default: #000;
--tw-inset-ring-shadow: 0 0 #0000;
--color-gray-300: hsla(0, 0%, 90%, 1);
--geist-secondary-lighter: #eaeaea;
--color-gray-500: hsla(0, 0%, 79%, 1);
--header-border-bottom: 0 1px 0 0 #0000001a;
--geist-secondary-dark: #333;
--ds-focus-ring: 0 0 0 2px hsla(0, 0%, 100%, 1), 0 0 0 4px hsla(212, 100%, 48%, 1);
--accents-3: #999;
--geist-selection-text-color: hsla(0, 0%, 95%, 1);
--accents-8: #111;
--color-zinc-900: lab(8.30603% .618205 -2.16572);
--accents-2: #eaeaea;
--color-gray-950: lab(1.90334% .278696 -5.48866);
--ds-shadow-border-small: 0 0 0 1px #00000014, 0px 2px 2px #0000000a, 0 0 0 1px hsla(0, 0%, 98%, 1);
--color-violet-50: lab(96.2416% 2.28849 -5.51657);
--tw-ring-shadow: 0 0 #0000;
--ds-shadow-background-border: 0 0 0 1px hsla(0, 0%, 98%, 1);
--geist-foreground-rgb: 0, 0, 0;
--geist-console-text-color-blue: #0070f3;
--tw-ring-offset-width: 0px;
--accents-4: #888;
--color-violet-700: lab(35.2783% 67.9912 -88.793);
--tw-ring-offset-shadow: 0 0 #0000;
--geist-secondary-light: #999;
--ds-motion-popover-timing: cubic-bezier(.175, .885, .32, 1.1);
--color-background-100: hsla(0, 0%, 100%, 1);
--color-violet-100: lab(93.0838% 4.35197 -9.88284);
--color-gray-900: hsla(0, 0%, 30%, 1);
--color-gray-700: hsla(0, 0%, 56%, 1);
--ds-motion-popover-duration: .2s;
--ds-shadow-border-medium: 0 0 0 1px #00000014, 0px 2px 2px #0000000a, 0px 8px 8px -8px #0000000a, 0 0 0 1px hsla(0, 0%, 98%, 1);
--color-zinc-100: lab(96.1634% .0993311 -.364041);
--color-slate-500: lab(48.0876% -2.03595 -16.5814);
--accents-6: #444;
--color-slate-300: lab(84.7652% -1.94535 -7.93337);
--ds-shadow-border: 0 0 0 1px #00000014, 0 0 0 1px hsla(0, 0%, 98%, 1);
--color-neutral-700: lab(27.036% 0 0);
--geist-violet-background-secondary: #291c3a;
--ds-overlay-backdrop-color: hsla(0, 0%, 98%, 1);
--ds-shadow-border-base: 0 0 0 1px #00000014;
--color-gray-alpha-400: #00000014;
--ds-shadow-border-inset: inset 0 0 0 1px #00000014;
--color-zinc-600: lab(35.1166% 1.78212 -6.1173);
--color-gray-600: hsla(0, 0%, 66%, 1);
--tw-border-style: solid;
--animate-fadeOutPopover: fadeOut cubic-bezier(.175, .885, .32, 1.1) .2s;
--ds-focus-color: hsla(212, 100%, 48%, 1);
--accents-7: #333;
--color-gray-1000: hsla(0, 0%, 9%, 1);
--color-gray-50: lab(98.2596% -.247031 -.706708);
--geist-console-text-color-purple: #7928ca;
--tw-ring-offset-color: #fff;
--geist-console-text-color-pink: #eb367f;
--accents-1: #fafafa;
--color-indigo-600: lab(38.4009% 52.6132 -92.3857);
--geist-secondary: #666;
--color-gray-800: hsla(0, 0%, 49%, 1);
--ds-focus-border: 0 0 0 1px #00000057, 0px 0px 0px 4px #00000029;
--accents-5: #666;
--geist-foreground: #000;
--color-red-50: lab(96.5005% 4.18508 1.52328);
--color-gray-200: hsla(0, 0%, 92%, 1);
--next-icon-border: #000;
--geist-link-color: hsla(212, 100%, 48%, 1);
--color-neutral-800: lab(15.204% 0 -.00000596046);
--color-amber-50: lab(98.6252% -.635922 8.42309);
```

### Spacing

```css
--geist-space-64x: 256px;
--geist-space-small-negative: -32px;
--tw-space-x-reverse: 0;
--spacing-fluid-24-40: clamp(1.5rem, -.2143rem + 2.8571vi, 2.5rem);
--geist-space-16x: 64px;
--geist-space-large-negative: -48px;
--geist-space-gap-half-negative: -12px;
--geist-gap-half: 12px;
--geist-space-24x: 96px;
--spacing-fluid-16-24: clamp(1rem, .1429rem + 1.4286vi, 1.5rem);
--geist-space-2x-negative: -8px;
--geist-space-gap-quarter-negative: -8px;
--geist-space-large: 48px;
--geist-gap-half-negative: -12px;
--geist-space-32x-negative: -128px;
--tw-space-y-reverse: 0;
--geist-space-8x-negative: -32px;
--geist-gap-quarter: 8px;
--geist-space-3x: 12px;
--geist-gap-quarter-negative: -8px;
--geist-space-small: 32px;
--geist-gap: 24px;
--geist-space-48x-negative: -192px;
--geist-space-negative: -4px;
--ds-page-width-with-margin: calc(1400px + calc(2 * 24px));
--geist-page-width-with-margin: calc(1200px + calc(2 * 24px));
--geist-gap-double: 48px;
--geist-space-16x-negative: -64px;
--geist-space-gap: 24px;
--geist-space-gap-negative: -24px;
--geist-space-4x: 16px;
--geist-space-medium: 40px;
--geist-space-gap-quarter: 8px;
--geist-space-24x-negative: -96px;
--geist-space-48x: 192px;
--geist-gap-section: 32px;
--spacing: .25rem;
--geist-space-gap-half: 12px;
--spacing-fluid-20-24: clamp(1.25rem, .8214rem + .7143vi, 1.5rem);
--geist-space: 4px;
--geist-gap-negative: -24px;
--geist-space-32x: 128px;
--geist-gap-double-negative: -48px;
--geist-page-margin: 24px;
--geist-space-6x: 24px;
--geist-space-8x: 32px;
--geist-space-4x-negative: -16px;
--geist-space-64x-negative: -256px;
--spacing-fluid-20-32: clamp(1.25rem, -.0357rem + 2.1429vi, 2rem);
--geist-space-10x: 40px;
--geist-space-medium-negative: -40px;
--geist-space-2x: 8px;
```

### Typography

```css
--font-sans: var(--font-geist-sans);
--font-mono: var(--font-geist-mono);
--ship-text: #ff5b4f;
--text-base--line-height: calc(1.5 / 1);
--tracking-wider: .05em;
--text-fluid-24-32: clamp(1.5rem, .6429rem + 1.4286vi, 2rem);
--text-fluid-24-28: clamp(1.5rem, 1.0714rem + .7143vi, 1.75rem);
--text-fluid-16-28: clamp(1rem, -.2857rem + 2.1429vi, 1.75rem);
--text-8xl: 6rem;
--text-sm: .875rem;
--geist-form-small-font: .875rem;
--font-weight-thin: 100;
--geist-form-large-font: 1rem;
--text-fluid-14-24: clamp(.875rem, -.1964rem + 1.7857vi, 1.5rem);
--text-lg: 1.125rem;
--text-8xl--line-height: 1;
--geist-form-small-line-height: .875rem;
--text-fluid-18-24: clamp(1.125rem, .4821rem + 1.0714vi, 1.5rem);
--default-font-family: "GeistSans", "GeistSans Fallback";
--tracking-tighter: -.05em;
--develop-text: #0a72ef;
--text-fluid-14-20: clamp(.875rem, .2321rem + 1.0714vi, 1.25rem);
--font-weight-extrabold: 800;
--text-sm--line-height: calc(1.25 / .875);
--text-3xl--line-height: calc(2.25 / 1.875);
--text-3xl: 1.875rem;
--text-xs: .75rem;
--font-weight-medium: 500;
--font-weight-normal: 400;
--font-sans-fallback: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif;
--text-base: 1rem;
--default-mono-font-family: "Geist Mono", ui-monospace, SFMono-Regular, Roboto Mono, Menlo, Monaco, Liberation Mono, DejaVu Sans Mono, Courier New, monospace, Apple Color Emoji, Segoe UI Emoji, Segoe UI Symbol;
--preview-text: #de1d8d;
--text-fluid-32-64: clamp(2rem, -1.4286rem + 5.7143vi, 4rem);
--geist-text-gradient: linear-gradient(180deg, #000c 0%, #000 100%);
--text-fluid-64-128: clamp(4rem, -2.8571rem + 11.4286vi, 8rem);
--text-fluid-20-28: clamp(1.25rem, .3929rem + 1.4286vi, 1.75rem);
--font-weight-bold: 700;
--text-xs--line-height: calc(1 / .75);
--text-fluid-20-32: clamp(1.25rem, -.0357rem + 2.1429vi, 2rem);
--text-xl: 1.25rem;
--leading-relaxed: 1.625;
--geist-form-line-height: 1.25rem;
--text-2xl--line-height: calc(2 / 1.5);
--text-xl--line-height: calc(1.75 / 1.25);
--font-mono-fallback: "Roboto Mono", Menlo, Monaco, Lucida Console, Liberation Mono, DejaVu Sans Mono, Bitstream Vera Sans Mono, Courier New, monospace;
--geist-form-font: .875rem;
--leading-tight: 1.25;
--font-geist-sans: "GeistSans", "GeistSans Fallback";
--text-fluid-20-80: clamp(1.25rem, -5.1786rem + 10.7143vi, 5rem);
--geist-form-large-line-height: 1.5rem;
--text-fluid-14-16: clamp(.875rem, .6607rem + .3571vi, 1rem);
--text-4xl--line-height: calc(2.5 / 2.25);
--tracking-tight: -.025em;
--text-2xl: 1.5rem;
--text-7xl: 4.5rem;
--text-fluid-16-20: clamp(1rem, .5714rem + .7143vi, 1.25rem);
--text-fluid-32-80: clamp(2rem, -3.1429rem + 8.5714vi, 5rem);
--text-5xl--line-height: 1;
--leading-normal: 1.5;
--text-lg--line-height: calc(1.75 / 1.125);
--font-weight-light: 300;
--text-7xl--line-height: 1;
--tracking-wide: .025em;
--font-weight-semibold: 600;
--text-4xl: 2.25rem;
--tracking-normal: 0em;
--text-5xl: 3rem;
```

### Shadows

```css
--tw-inset-shadow: 0 0 #0000;
--dropdown-box-shadow: 0 4px 4px 0 #00000005;
--tw-shadow-alpha: 100%;
--ds-shadow-large: 0px 2px 2px #0000000a, 0px 8px 16px -4px #0000000a;
--shadow-sticky: 0 12px 10px -10px #0000001f;
--tw-drop-shadow-alpha: 100%;
--shadow-large: 0 30px 60px #0000001f;
--ds-shadow-small: 0px 2px 2px #0000000a;
--shadow-medium: 0 8px 30px #0000001f;
--ds-shadow-xl: 0px 1px 1px #00000005, 0px 4px 8px -4px #0000000a, 0px 16px 24px -8px #0000000f;
--ds-shadow-modal: 0 0 0 1px #00000014, 0px 1px 1px #00000005, 0px 8px 16px -4px #0000000a, 0px 24px 32px -8px #0000000f, 0 0 0 1px hsla(0, 0%, 98%, 1);
--ds-shadow-medium: 0px 2px 2px #0000000a, 0px 8px 8px -8px #0000000a;
--tw-shadow: 0 0 #0000;
--shadow-hover: 0 30px 60px #0000001f;
--tw-inset-shadow-alpha: 100%;
--ds-shadow-2xl: 0px 1px 1px #00000005, 0px 8px 16px -4px #0000000a, 0px 24px 32px -8px #0000000f;
--drop-shadow-lg: 0 4px 4px #00000026;
--shadow-smallest: 0px 2px 4px #0000001a;
--ds-shadow-tooltip: 0 0 0 1px #00000014, 0px 1px 1px #00000005, 0px 4px 8px #0000000a, 0 0 0 1px hsla(0, 0%, 98%, 1);
--ds-shadow-xs: 0px 1px 2px #0000000a;
--ds-shadow-2xs: 0px 1px 1px #0000000a;
--shadow-small: 0 5px 10px #0000001f;
--ds-shadow-fullscreen: 0 0 0 1px #00000014, 0px 1px 1px #00000005, 0px 8px 16px -4px #0000000a, 0px 24px 32px -8px #0000000f, 0 0 0 1px hsla(0, 0%, 98%, 1);
--shadow-extra-small: 0px 4px 8px #0000001f;
--ds-shadow-menu: 0 0 0 1px #00000014, 0px 1px 1px #00000005, 0px 4px 8px -4px #0000000a, 0px 16px 24px -8px #0000000f, 0 0 0 1px hsla(0, 0%, 98%, 1);
```

### Radii

```css
--geist-radius: 6px;
--geist-marketing-radius: 8px;
--radius-3xl: 1.5rem;
```

### Other

```css
--banner-min-height: 64px;
--blur-lg: 16px;
--geist-cyan-lighter: #aaffec;
--ds-amber-700: hsla(39, 100%, 57%, 1);
--ds-pink-300-value: 340, 82%, 94%;
--ease-in: cubic-bezier(.4, 0, 1, 1);
--geist-error: #e00;
--ds-amber-900: hsla(30, 100%, 32%, 1);
--ds-green-200: hsla(120, 60%, 95%, 1);
--tw-enter-scale: 1;
--ds-red-800-value: 358, 70%, 52%;
--geist-violet-lighter: #d8ccf1;
--ds-green-1000: hsla(128, 29%, 15%, 1);
--ds-red-1000: hsla(355, 49%, 15%, 1);
--wv-orange: #ffa400;
--ds-amber-800-value: 35, 100%, 52%;
--ds-gray-alpha-600: #00000057;
--animate-cmdkScaleIn: cmdkScaleIn .3s cubic-bezier(.175, .885, .32, 1.1);
--ds-pink-300: hsla(340, 82%, 94%, 1);
--develop-start-gradient: #007cf0;
--geist-violet-background-tertiary: #eae5f4;
--ds-gray-alpha-100: #0000000d;
--ds-teal-700-value: 173, 80%, 36%;
--tw-exit-translate-y: 0;
--ds-blue-1000: hsla(211, 100%, 15%, 1);
--tw-gradient-to-position: 100%;
--ds-amber-600: hsla(36, 90%, 62%, 1);
--ds-white: lab(100% 0 0);
--animate-sandbox-left-reverse: sandbox-left-reverse .5s ease-in-out forwards;
--ds-background-200: hsla(0, 0%, 98%, 1);
--ds-red-500-value: 0, 82%, 85%;
--dropdown-triangle-stroke: #fff;
--ds-blue-400: hsla(209, 100%, 90%, 1);
--animate-flip-front: flip-front .5s cubic-bezier(.4, .04, .04, 1) forwards;
--ds-teal-700: hsla(173, 80%, 36%, 1);
--geist-highlight-magenta: #eb367f;
--ds-red-200: hsla(0, 100%, 96%, 1);
--ds-green-800: hsla(132, 43%, 39%, 1);
--ds-purple-1000: hsla(276, 100%, 15%, 1);
--vh100-offset: calc(64px + 0px);
--ds-green-100-value: 120, 60%, 96%;
--ds-gray-500: hsla(0, 0%, 79%, 1);
--scroller-start: #fff;
--ds-purple-800: hsla(272, 47%, 45%, 1);
--ds-purple-300: hsla(274, 78%, 95%, 1);
--ds-amber-500: hsla(38, 100%, 71%, 1);
--tw-scale-y: 1;
--animate-cmdkFadeIn: cmdkFadeIn .3s cubic-bezier(.175, .885, .32, 1.1);
--ds-red-700-value: 358, 75%, 59%;
--scroller-end: #fff0;
--geist-background-rgb: 255, 255, 255;
--tw-exit-translate-x: 0;
--ds-blue-1000-value: 211, 100%, 15%;
--ds-pink-500-value: 340, 75%, 84%;
--ds-blue-200-value: 210, 100%, 96%;
--header-zindex: 75;
--ds-gray-500-value: 0, 0%, 79%;
--ds-blue-100: hsla(212, 100%, 97%, 1);
--ds-gray-700: hsla(0, 0%, 56%, 1);
--ds-teal-800-value: 173, 83%, 30%;
--animate-sandbox-left: sandbox-left .5s ease-in-out forwards;
--ds-amber-700-value: 39, 100%, 57%;
--ds-teal-200-value: 167, 70%, 94%;
--ds-purple-400-value: 276, 71%, 92%;
--ds-contrast-fg: #fff;
--tw-enter-blur: 0;
--ds-amber-1000-value: 20, 79%, 17%;
--animate-cmdkScaleOut: cmdkScaleOut .3s cubic-bezier(.175, .885, .32, 1.1);
--ds-red-700: hsla(358, 75%, 59%, 1);
--container-xl: 1200px;
--geist-highlight-purple: #f81ce5;
--ds-red-400-value: 0, 90%, 92%;
--ds-teal-500: hsla(170, 70%, 72%, 1);
--geist-code: #000;
--ds-gray-1000-value: 0, 0%, 9%;
--ds-teal-1000-value: 171, 80%, 13%;
--ds-blue-800-value: 212, 100%, 41%;
--geist-warning-lighter: #ffefcf;
--tw-animation-direction: normal;
--ds-blue-400-value: 209, 100%, 90%;
--ds-pink-900-value: 336, 65%, 45%;
--animate-feedbackFadeIn: feedbackFadeIn .1s cubic-bezier(.16, 1, .3, 1);
--geist-page-width: 1200px;
--ds-purple-100: hsla(276, 100%, 97%, 1);
--ds-gray-200-value: 0, 0%, 92%;
--ds-red-500: hsla(0, 82%, 85%, 1);
--tw-divide-x-reverse: 0;
--ds-blue-600-value: 208, 100%, 66%;
--animate-slide-in: slide-in 1.25s cubic-bezier(.4, .04, .04, 1) forwards;
--preview-end-gradient: #ff0080;
--tw-exit-rotate: 0;
--develop-end-gradient: #00dfd8;
--ds-purple-600-value: 273, 72%, 73%;
--ds-blue-700: hsla(212, 100%, 48%, 1);
--ds-purple-300-value: 274, 78%, 95%;
--ds-amber-600-value: 36, 90%, 62%;
--container-sm: 401px;
--ds-green-100: hsla(120, 60%, 96%, 1);
--animate-feedbackAppear: feedbackAppear .5s .1s ease forwards;
--ds-gray-alpha-800: #00000082;
--animate-loading-skeleton: loading-skeleton 1.5s ease-in-out infinite reverse;
--ds-gray-900-value: 0, 0%, 30%;
--header-sub-menu-height: 46px;
--ds-gray-200: hsla(0, 0%, 92%, 1);
--ds-overlay-backdrop-opacity: .8;
--ds-blue-500-value: 209, 100%, 80%;
--animate-flip-back: flip-back .5s cubic-bezier(.4, .04, .04, 1) forwards;
--ds-green-700: hsla(131, 41%, 46%, 1);
--ds-amber-100-value: 39, 100%, 95%;
--ds-pink-200: hsla(340, 90%, 96%, 1);
--tw-gradient-from-position: 0%;
--ds-pink-700: hsla(336, 80%, 58%, 1);
--ds-blue-300: hsla(210, 100%, 94%, 1);
--wv-green: #0cce6b;
--ds-gray-700-value: 0, 0%, 56%;
--ds-gray-alpha-700: #00000070;
--ds-gray-300-value: 0, 0%, 90%;
--ds-pink-1000: hsla(333, 74%, 15%, 1);
--ds-red-300-value: 0, 100%, 95%;
--ds-gray-alpha-400: #00000014;
--animate-thinking-loader-fast: thinking-loader .85s linear infinite;
--geist-console-purple: #7928ca;
--ds-purple-900-value: 274, 71%, 43%;
--ds-gray-400-value: 0, 0%, 92%;
--tw-animation-fill-mode: none;
--tw-exit-blur: 0;
--animate-feedbackFadeOut: feedbackFadeOut .2s cubic-bezier(.16, 1, .3, 1) forwards;
--ds-pink-500: hsla(340, 75%, 84%, 1);
--ds-red-900-value: 358, 66%, 48%;
--ds-pink-100-value: 330, 100%, 96%;
--geist-highlight-pink: #ff0080;
--geist-cyan-light: #79ffe1;
--ds-green-600: hsla(125, 60%, 64%, 1);
--ds-red-1000-value: 355, 49%, 15%;
--ds-green-900: hsla(133, 50%, 32%, 1);
--geist-cyan: #50e3c2;
--ds-pink-900: hsla(336, 65%, 45%, 1);
--tw-enter-translate-x: 0;
--container-4xl: 56rem;
--ds-purple-1000-value: 276, 100%, 15%;
--animate-fade-in: fade-in 1.25s cubic-bezier(.4, .04, .04, 1) forwards;
--ds-amber-800: hsla(35, 100%, 52%, 1);
--ds-green-700-value: 131, 41%, 46%;
--preview-line-end: #9a1fb8;
--ds-amber-400-value: 42, 100%, 78%;
--ds-gray-alpha-500: #00000036;
--ds-green-300: hsla(120, 60%, 91%, 1);
--animate-fadeInTooltipFaster: fadeInTooltip .1s ease-in .1s forwards;
--ds-green-300-value: 120, 60%, 91%;
--ds-blue-900: hsla(211, 100%, 42%, 1);
--ds-gray-600: hsla(0, 0%, 66%, 1);
--ds-purple-500: hsla(274, 70%, 82%, 1);
--ds-green-400: hsla(122, 60%, 86%, 1);
--ds-pink-800: hsla(336, 74%, 51%, 1);
--ds-blue-500: hsla(209, 100%, 80%, 1);
--ds-green-900-value: 133, 50%, 32%;
--animate-blink: blink 1s infinite;
--ds-amber-300-value: 43, 96%, 90%;
--ds-amber-400: hsla(42, 100%, 78%, 1);
--tw-enter-opacity: 1;
--ds-motion-overlay-scale: .96;
--geist-form-height: 40px;
--container-md: 601px;
--header-height: 64px;
--aspect-video: 16 / 9;
--ds-teal-100: hsla(169, 70%, 96%, 1);
--ds-green-1000-value: 128, 29%, 15%;
--develop-line-end: #019ae9;
--ds-blue-600: hsla(208, 100%, 66%, 1);
--animate-loading: loading 8s ease-in-out infinite;
--tw-animation-delay: 0s;
--animate-marquee: marquee 40s linear infinite;
--ds-green-800-value: 132, 43%, 39%;
--ds-amber-500-value: 38, 100%, 71%;
--geist-success-light: #3291ff;
--tw-outline-style: solid;
--geist-warning-light: #f7b955;
--geist-cyan-dark: #29bc9b;
--geist-success-dark: #0761d1;
--geist-form-small-height: 32px;
--header-import-flow-background: #fafafacc;
--ds-black: lab(0% 0 0);
--ds-pink-200-value: 340, 90%, 96%;
--ds-blue-200: hsla(210, 100%, 96%, 1);
--tw-gradient-from: rgba(0, 0, 0, 0);
--tw-gradient-to: rgba(0, 0, 0, 0);
--ds-pink-600: hsla(341, 75%, 73%, 1);
--ds-gray-800: hsla(0, 0%, 49%, 1);
--geist-violet-light: #8a63d2;
--ds-teal-1000: hsla(171, 80%, 13%, 1);
--ds-gray-300: hsla(0, 0%, 90%, 1);
--ds-purple-600: hsla(273, 72%, 73%, 1);
--tw-gradient-via-position: 50%;
--ds-amber-1000: hsla(20, 79%, 17%, 1);
--ds-amber-200: hsla(44, 100%, 92%, 1);
--ds-teal-300-value: 168, 70%, 90%;
--default-transition-duration: .15s;
--animate-pulse: pulse 2s cubic-bezier(.4, 0, .6, 1) infinite;
--ds-pink-700-value: 336, 80%, 58%;
--container-xs: 20rem;
--ds-gray-1000: hsla(0, 0%, 9%, 1);
--ds-purple-200-value: 277, 87%, 97%;
--ds-teal-400-value: 170, 70%, 85%;
--ds-green-600-value: 125, 60%, 64%;
--banner-height: 0px;
--ds-red-200-value: 0, 100%, 96%;
--ds-blue-900-value: 211, 100%, 42%;
--default-transition-timing-function: cubic-bezier(.4, 0, .2, 1);
--tw-animation-iteration-count: 1;
--tw-exit-opacity: 1;
--ds-teal-500-value: 170, 70%, 72%;
--ds-motion-overlay-timing: cubic-bezier(.175, .885, .32, 1.1);
--ds-pink-800-value: 336, 74%, 51%;
--tw-translate-z: 0;
--tw-gradient-via: rgba(0, 0, 0, 0);
--ds-pink-400: hsla(341, 76%, 91%, 1);
--geist-violet-dark: #4c2889;
--ai-chat-panel-width: 0px;
--container-3xl: 48rem;
--blur-xs: 4px;
--tw-translate-y: 0;
--ease-out: cubic-bezier(0, 0, .2, 1);
--ship-start-gradient: #ff4d4d;
--ds-gray-100: hsla(0, 0%, 95%, 1);
--ds-page-width: 1400px;
--tw-content: "";
--ds-teal-100-value: 169, 70%, 96%;
--animate-thinking-loader: thinking-loader 1.5s linear infinite;
--ds-purple-500-value: 274, 70%, 82%;
--ds-teal-300: hsla(168, 70%, 90%, 1);
--tw-translate-x: 0;
--tw-enter-rotate: 0;
--ds-gray-100-value: 0, 0%, 95%;
--ds-gray-alpha-1000: #000000e8;
--geist-error-lighter: #f7d4d6;
--animate-bounce: bounce 1s infinite;
--animate-fade-slide-in: fade-slide-in .35s cubic-bezier(.16, 1, .3, 1) forwards;
--ds-red-300: hsla(0, 100%, 95%, 1);
--ds-purple-900: hsla(274, 71%, 43%, 1);
--ds-background-100: hsla(0, 0%, 100%, 1);
--ds-gray-alpha-300: #0000001a;
--animate-fadeInTooltip: fadeInTooltip .1s ease-in .4s forwards;
--ds-red-400: hsla(0, 90%, 92%, 1);
--geist-marketing-gray: #fafbfc;
--ds-red-600: hsla(359, 90%, 71%, 1);
--ds-blue-300-value: 210, 100%, 94%;
--ds-teal-900-value: 174, 91%, 25%;
--ds-motion-timing-swift: cubic-bezier(.175, .885, .32, 1.1);
--ds-pink-400-value: 341, 76%, 91%;
--ds-pink-1000-value: 333, 74%, 15%;
--ds-purple-400: hsla(276, 71%, 92%, 1);
--ds-blue-800: hsla(212, 100%, 41%, 1);
--ds-amber-900-value: 30, 100%, 32%;
--geist-form-large-height: 48px;
--animate-ping: ping 1s cubic-bezier(0, 0, .2, 1) infinite;
--geist-warning: #f5a623;
--geist-error-dark: #c50000;
--ds-motion-overlay-duration: .3s;
--ds-purple-800-value: 272, 47%, 45%;
--wv-red: #ff4e42;
--ds-gray-alpha-900: #000000b3;
--ds-gray-900: hsla(0, 0%, 30%, 1);
--geist-violet: #7928ca;
--ship-line-end: #f9cb28;
--geist-console-header: #efe7ed;
--blur-xl: 24px;
--geist-success-lighter: #d3e5ff;
--ds-red-100-value: 0, 100%, 97%;
--geist-error-light: #ff1a1a;
--animate-accordion-down: accordion-down .2s ease-out;
--ds-purple-100-value: 276, 100%, 97%;
--tw-scale-z: 1;
--ds-red-800: hsla(358, 70%, 52%, 1);
--ds-purple-700-value: 272, 51%, 54%;
--ds-amber-300: hsla(43, 96%, 90%, 1);
--tw-scroll-snap-strictness: proximity;
--ds-background-200-value: 0, 0%, 98%;
--container-lg: 961px;
--ds-green-500: hsla(124, 60%, 75%, 1);
--geist-highlight-yellow: #fff500;
--ds-green-400-value: 122, 60%, 86%;
--ds-pink-100: hsla(330, 100%, 96%, 1);
--ds-blue-700-value: 212, 100%, 48%;
--ds-teal-600: hsla(170, 70%, 57%, 1);
--geist-success: #0070f3;
--ds-gray-alpha-200: #00000014;
--animate-command-fade-in: fade-in .2s ease-out forwards;
--ds-green-500-value: 124, 60%, 75%;
--ds-gray-400: hsla(0, 0%, 92%, 1);
--ease-in-out: cubic-bezier(.4, 0, .2, 1);
--animate-cmdkFadeOut: cmdkFadeOut .3s cubic-bezier(.175, .885, .32, 1.1);
--ds-gray-600-value: 0, 0%, 66%;
--value: 0;
--animate-accordion-up: accordion-up .2s ease-out;
--animate-sandbox-right: sandbox-right .5s ease-in-out forwards;
--preview-start-gradient: #7928ca;
--animate-logo-carousel: logo-carousel ease-in-out infinite;
--ds-teal-900: hsla(174, 91%, 25%, 1);
--container-5xl: 64rem;
--ds-amber-100: hsla(39, 100%, 95%, 1);
--animate-sandbox-right-reverse: sandbox-right-reverse .5s ease-in-out forwards;
--footer-height: 79px;
--ds-red-900: hsla(358, 66%, 48%, 1);
--geist-background: #fff;
--perspective-distant: 1200px;
--ds-background-100-value: 0, 0%, 100%;
--ds-red-600-value: 359, 90%, 71%;
--geist-selection: hsla(0, 0%, 9%, 1);
--ds-teal-400: hsla(170, 70%, 85%, 1);
--ds-purple-700: hsla(272, 51%, 54%, 1);
--geist-warning-dark: #ab570a;
--ds-gray-800-value: 0, 0%, 49%;
--ds-blue-100-value: 212, 100%, 97%;
--tw-divide-y-reverse: 0;
--ds-teal-200: hsla(167, 70%, 94%, 1);
--container-2xl: 1400px;
--tw-exit-scale: 1;
--ds-purple-200: hsla(277, 87%, 97%, 1);
--ds-amber-200-value: 44, 100%, 92%;
--tw-enter-translate-y: 0;
--tw-scale-x: 1;
--ds-teal-600-value: 170, 70%, 57%;
--ds-green-200-value: 120, 60%, 95%;
--ship-end-gradient: #f9cb28;
--ds-red-100: hsla(0, 100%, 97%, 1);
--geist-violet-background: #fff;
--ds-pink-600-value: 341, 75%, 73%;
--ds-teal-800: hsla(173, 83%, 30%, 1);
--blur-sm: 8px;
--animate-cmdkLoading: cmdkLoading 1.1s cubic-bezier(.455, .03, .515, .955) infinite;
```

### Dependencies

```css
--font-sans: --font-geist-sans;
--font-mono: --font-geist-mono;
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
| xs | 370px | max-width |
| xs | 380px | max-width |
| xs | 383px | max-width |
| 400px | 400px | max-width |
| sm | 440px | max-width |
| sm | 450px | max-width |
| sm | 470px | min-width |
| sm | 480px | max-width |
| sm | 500px | max-width |
| sm | 600px | max-width |
| sm | 601px | max-width |
| sm | 640px | max-width |
| sm | 670px | max-width |
| md | 768px | max-width |
| md | 769px | min-width |
| md | 800px | max-width |
| lg | 960px | max-width |
| lg | 961px | min-width |
| lg | 992px | min-width |
| lg | 1024px | max-width |
| lg | 1036px | min-width |
| lg | 1050px | max-width |
| lg | 1080px | max-width |
| 1108px | 1108px | max-width |
| 1150px | 1150px | max-width |
| 1151px | 1151px | min-width |
| 1200px | 1200px | min-width |
| 2300px | 2300px | min-width |

## Transitions & Animations

**Easing functions:** `[object Object]`, `[object Object]`, `[object Object]`, `[object Object]`, `[object Object]`, `[object Object]`

**Durations:** `0.15s`, `0.7s`, `1.2s`, `0.2s`, `0.5s`, `0.3s`, `0.4s`, `0.1s`, `1s`, `0.25s`

### Common Transitions

```css
transition: all;
transition: opacity 0.15s cubic-bezier(0.4, 0, 0.2, 1);
transition: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
transition: color 0.15s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.15s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.15s cubic-bezier(0.4, 0, 0.2, 1), outline-color 0.15s cubic-bezier(0.4, 0, 0.2, 1), text-decoration-color 0.15s cubic-bezier(0.4, 0, 0.2, 1), fill 0.15s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.15s cubic-bezier(0.4, 0, 0.2, 1), --tw-gradient-from 0.15s cubic-bezier(0.4, 0, 0.2, 1), --tw-gradient-via 0.15s cubic-bezier(0.4, 0, 0.2, 1), --tw-gradient-to 0.15s cubic-bezier(0.4, 0, 0.2, 1);
transition: opacity 0.7s linear;
transition: opacity 1.2s linear;
transition: height 0.2s cubic-bezier(0, 0, 0.2, 1);
transition: color 0.5s cubic-bezier(0, 0, 0.2, 1), background-color 0.5s cubic-bezier(0, 0, 0.2, 1), border-color 0.5s cubic-bezier(0, 0, 0.2, 1), outline-color 0.5s cubic-bezier(0, 0, 0.2, 1), text-decoration-color 0.5s cubic-bezier(0, 0, 0.2, 1), fill 0.5s cubic-bezier(0, 0, 0.2, 1), stroke 0.5s cubic-bezier(0, 0, 0.2, 1), --tw-gradient-from 0.5s cubic-bezier(0, 0, 0.2, 1), --tw-gradient-via 0.5s cubic-bezier(0, 0, 0.2, 1), --tw-gradient-to 0.5s cubic-bezier(0, 0, 0.2, 1);
transition: opacity 0.3s cubic-bezier(0, 0, 0.2, 1);
transition: color 0.15s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.15s cubic-bezier(0.4, 0, 0.2, 1);
```

### Keyframe Animations

**soft-fade-in**
```css
@keyframes soft-fade-in {
  0% { opacity: 0.3; }
  100% { opacity: 1; }
}
```

**show**
```css
@keyframes show {
  0% { transform: translate3d(0, var(--translate-y-start), 0); opacity: 0; }
  100% { transform: translate3d(0, var(--translate-y-end), 0); opacity: 1; }
}
```

**hide**
```css
@keyframes hide {
  0% { transform: translate3d(0, var(--translate-y-end), 0); opacity: 1; }
  100% { transform: translate3d(0, var(--translate-y-start), 0); opacity: 0; }
}
```

**fade-in**
```css
@keyframes fade-in {
  0% { opacity: 0; }
  100% { opacity: 1; }
}
```

**fade-out**
```css
@keyframes fade-out {
  0% { opacity: 1; }
  100% { opacity: 0; }
}
```

**spinner-opacity**
```css
@keyframes spinner-opacity {
  0% { opacity: 1; }
  100% { opacity: 0.15; }
}
```

**slide-in**
```css
@keyframes slide-in {
  0% { opacity: 0; transform: translateY(75%); }
  100% { opacity: 1; transform: translateY(0px); }
}
```

**fade-slide-in**
```css
@keyframes fade-slide-in {
  0% { opacity: 0; transform: translateY(-8px); }
  100% { opacity: 1; transform: translateY(0px); }
}
```

**blue-glow**
```css
@keyframes blue-glow {
  0%, 100% { box-shadow: 0 0 10px var(--ds-blue-200), 0 0 20px var(--ds-blue-100); }
  50% { box-shadow: 0 0 30px var(--ds-blue-400), 0 0 60px var(--ds-blue-200); }
}
```

**thinking-loader**
```css
@keyframes thinking-loader {
  0% { background-position: 100% center; }
  100% { background-position: 0% center; }
}
```

## Component Patterns

Detected UI component patterns and their most common styles:

### Buttons (10 instances)

```css
.button {
  background-color: rgb(255, 255, 255);
  color: rgb(23, 23, 23);
  font-size: 14px;
  font-weight: 400;
  padding-top: 0px;
  padding-right: 12px;
  border-radius: 4px;
}
```

### Cards (7 instances)

```css
.card {
  background-color: rgb(255, 255, 255);
  border-radius: 6px;
  box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.08) 0px 0px 0px 1px, rgb(250, 250, 250) 0px 0px 0px 1px;
  padding-top: 0px;
  padding-right: 0px;
}
```

### Inputs (3 instances)

```css
.input {
  color: rgb(23, 23, 23);
  border-color: rgb(235, 235, 235);
  border-radius: 0px;
  font-size: 14px;
  padding-top: 0px;
  padding-right: 0px;
}
```

### Links (162 instances)

```css
.link {
  color: rgb(102, 102, 102);
  font-size: 14px;
  font-weight: 400;
}
```

### Navigation (10 instances)

```css
.navigatio {
  background-color: rgb(250, 250, 250);
  color: rgb(23, 23, 23);
  padding-top: 0px;
  padding-bottom: 0px;
  padding-left: 0px;
  padding-right: 0px;
  position: fixed;
  box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.1) 0px 1px 0px 0px;
}
```

### Footer (1 instances)

```css
.foote {
  color: rgb(23, 23, 23);
  padding-top: 40px;
  padding-bottom: 40px;
  font-size: 14px;
}
```

### Modals (1 instances)

```css
.modal {
  background-color: rgb(255, 255, 255);
  border-radius: 0px;
  padding-top: 0px;
  padding-right: 0px;
}
```

### Dropdowns (8 instances)

```css
.dropdown {
  background-color: rgb(255, 255, 255);
  border-radius: 3.35544e+07px;
  box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.04) 0px 2px 2px 0px, rgba(0, 0, 0, 0.04) 0px 8px 16px -4px;
  border-color: rgb(235, 235, 235);
  padding-top: 0px;
}
```

### Badges (14 instances)

```css
.badge {
  color: rgb(23, 23, 23);
  font-size: 14px;
  font-weight: 500;
  padding-top: 0px;
  padding-right: 0px;
  border-radius: 0px;
}
```

### Accordions (4 instances)

```css
.accordion {
  color: rgb(23, 23, 23);
  font-size: 16px;
  padding-top: 0px;
  padding-right: 0px;
  border-color: rgb(235, 235, 235);
}
```

### Tooltips (1 instances)

```css
.tooltip {
  background-color: rgb(255, 255, 255);
  color: rgb(23, 23, 23);
  font-size: 16px;
  border-radius: 6px;
  padding-top: 0px;
  padding-right: 0px;
  box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.08) 0px 0px 0px 1px, rgba(0, 0, 0, 0.02) 0px 1px 1px 0px, rgba(0, 0, 0, 0.04) 0px 4px 8px 0px, rgb(250, 250, 250) 0px 0px 0px 1px, rgb(255, 255, 255) 0px 0px 0px 1px;
}
```

## Component Clusters

Reusable component instances grouped by DOM structure and style similarity:

### Button — 3 instances, 2 variants

**Variant 1** (2 instances)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(77, 77, 77);
  padding: 0px 0px 0px 0px;
  border-radius: 0px;
  border: 0px none rgb(235, 235, 235);
  font-size: 14px;
  font-weight: 400;
```

**Variant 2** (1 instance)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(77, 77, 77);
  padding: 6px 4px 6px 6px;
  border-radius: 3.35544e+07px;
  border: 0px solid rgb(235, 235, 235);
  font-size: 14px;
  font-weight: 400;
```

### Button — 6 instances, 1 variant

**Variant 1** (6 instances)

```css
  background: rgb(255, 255, 255);
  color: rgb(77, 77, 77);
  padding: 0px 0px 0px 0px;
  border-radius: 3.35544e+07px;
  border: 0px solid rgb(235, 235, 235);
  font-size: 14px;
  font-weight: 400;
```

### Button — 1 instance, 1 variant

**Variant 1** (1 instance)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(168, 168, 168);
  padding: 14px 14px 14px 14px;
  border-radius: 3.35544e+07px;
  border: 0px none rgb(235, 235, 235);
  font-size: 16px;
  font-weight: 400;
```

### Button — 1 instance, 1 variant

**Variant 1** (1 instance)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(77, 77, 77);
  padding: 2px 2px 2px 2px;
  border-radius: 0px;
  border: 0px solid rgb(235, 235, 235);
  font-size: 14px;
  font-weight: 400;
```

## Layout System

**12 grid containers** and **349 flex containers** detected.

### Container Widths

| Max Width | Padding |
|-----------|---------|
| 1280px | 0px |
| 1448px | 24px |
| 1080px | 0px |
| 100% | 0px |

### Grid Column Patterns

| Columns | Usage Count |
|---------|-------------|
| 12-column | 9x |
| 5-column | 2x |
| 1-column | 1x |

### Grid Templates

```css
grid-template-columns: 80.6562px 80.6562px 80.6562px 80.6562px 80.6562px 80.6562px 80.6719px 80.6719px 80.6562px 80.6562px 80.6562px 80.6562px;
gap: 24px;
grid-template-columns: 84.1562px 84.1562px 84.1562px 84.1562px 84.1562px 84.1562px 84.1562px 84.1562px 84.1562px 84.1562px 84.1562px 84.1562px;
gap: 20px;
grid-template-columns: 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3438px 84.3281px 84.3281px 84.3281px;
gap: normal 20px;
grid-template-columns: 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px;
gap: normal 20px;
grid-template-columns: 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3281px 84.3438px 84.3281px 84.3281px 84.3281px;
gap: normal 20px;
```

### Flex Patterns

| Direction/Wrap | Count |
|----------------|-------|
| row/nowrap | 301x |
| column/nowrap | 48x |

**Gap values:** `12px`, `16px`, `16px normal`, `20px`, `24px`, `256px`, `32px`, `3px`, `40px`, `44px`, `48px`, `4px`, `4px 20px`, `6px`, `8px`, `normal 16px`, `normal 20px`, `normal 32px`

## Responsive Design

### Viewport Snapshots

| Viewport | Body Font | Nav Visible | Max Columns | Hamburger | Page Height |
|----------|-----------|-------------|-------------|-----------|-------------|
| mobile (375px) | 16px | No | 12 | Yes | 4927px |
| tablet (768px) | 16px | No | 12 | Yes | 5717px |
| desktop (1280px) | 16px | Yes | 12 | No | 5127px |
| wide (1920px) | 16px | Yes | 12 | No | 5519px |

### Breakpoint Changes

**375px → 768px** (mobile → tablet):
- H1 size: `48px` → `64px`
- Page height: `4927px` → `5717px`

**768px → 1280px** (tablet → desktop):
- Nav visibility: `hidden` → `visible`
- Hamburger menu: `shown` → `hidden`
- Page height: `5717px` → `5127px`

**1280px → 1920px** (desktop → wide):
- Page height: `5127px` → `5519px`

## Interaction States

### Button States

**"Products"**
```css
/* Hover */
color: rgb(77, 77, 77) → rgb(23, 23, 23);
outline: rgb(77, 77, 77) none 3px → rgb(23, 23, 23) none 3px;
```
```css
/* Focus */
color: rgb(77, 77, 77) → rgb(23, 23, 23);
outline: rgb(77, 77, 77) none 3px → rgb(0, 95, 204) none 1px;
```

**"Resources"**
```css
/* Hover */
color: rgb(77, 77, 77) → rgb(23, 23, 23);
outline: rgb(77, 77, 77) none 3px → rgb(23, 23, 23) none 3px;
```
```css
/* Focus */
color: rgb(77, 77, 77) → rgb(23, 23, 23);
outline: rgb(77, 77, 77) none 3px → rgb(0, 95, 204) none 1px;
```

**"PluginPlugin"**
```css
/* Hover */
color: rgb(77, 77, 77) → rgb(27, 27, 27);
background-color: rgba(0, 0, 0, 0) → rgba(0, 0, 0, 0.047);
```
```css
/* Focus */
color: rgb(77, 77, 77) → rgb(23, 23, 23);
background-color: rgba(0, 0, 0, 0) → rgba(0, 0, 0, 0.05);
outline: rgba(0, 0, 0, 0) solid 2px → rgb(0, 114, 245) solid 2px;
```

## Accessibility (WCAG 2.1)

**Overall Score: 0%** — 0 passing, 1 failing color pairs

### Failing Color Pairs

| Foreground | Background | Ratio | Level | Used On |
|------------|------------|-------|-------|---------|
| `#0072f5` | `#ffffff` | 4.44:1 | FAIL | a (1x) |

## Design System Score

**Overall: 79/100 (Grade: C)**

| Category | Score |
|----------|-------|
| Color Discipline | 100/100 |
| Typography Consistency | 90/100 |
| Spacing System | 100/100 |
| Shadow Consistency | 90/100 |
| Border Radius Consistency | 100/100 |
| Accessibility | 0/100 |
| CSS Tokenization | 100/100 |

**Strengths:** Tight, disciplined color palette, Consistent typography system, Well-defined spacing scale, Clean elevation system, Consistent border radii, Good CSS variable tokenization

**Issues:**
- 1 WCAG contrast failures
- 1226 !important rules — prefer specificity over overrides
- 10607 duplicate CSS declarations

## Gradients

**7 unique gradients** detected.

| Type | Direction | Stops | Classification |
|------|-----------|-------|----------------|
| linear | to top in oklab | 2 | brand |
| radial | circle at 0% 0% | 2 | brand |
| radial | circle at 100% 0% | 2 | brand |
| radial | circle at 100% 100% | 2 | brand |
| linear | to top | 2 | brand |
| linear | to right | 2 | brand |
| linear | to right in oklab | 2 | brand |

```css
background: linear-gradient(to top in oklab, rgb(250, 250, 250) 0%, rgba(0, 0, 0, 0) 100%);
background: radial-gradient(circle at 0% 0%, rgb(250, 250, 250) 0%, rgba(0, 0, 0, 0) 30%);
background: radial-gradient(circle at 100% 0%, rgb(250, 250, 250) 0%, rgba(0, 0, 0, 0) 30%);
background: radial-gradient(circle at 100% 100%, rgb(250, 250, 250) 0%, rgba(0, 0, 0, 0) 30%);
background: linear-gradient(to top, rgb(250, 250, 250) 0%, oklab(0 0 0 / 0) 100%);
```

## Z-Index Map

**13 unique z-index values** across 4 layers.

| Layer | Range | Elements |
|-------|-------|----------|
| modal | 1000,999999999 | a.f.i.x.e.d. .-.m.-.p.x. .o.v.e.r.f.l.o.w.-.h.i.d.d.e.n. .w.h.i.t.e.s.p.a.c.e.-.n.o.w.r.a.p. .b.o.r.d.e.r.-.0. .t.o.p.-.1.6. .l.e.f.t.-.1.2. .z.-.[.1.0.0.0.]. .f.l.e.x. .i.t.e.m.s.-.c.e.n.t.e.r. .o.u.t.l.i.n.e.-.n.o.n.e. .t.e.x.t.-.[.v.a.r.(.-.-.g.e.i.s.t.-.l.i.n.k.-.c.o.l.o.r.).]. .p.x.-.1. .p.y.-.0. .b.g.-.[.v.a.r.(.-.-.g.e.i.s.t.-.b.a.c.k.g.r.o.u.n.d.).]. .s.h.a.d.o.w.-.[.0._.0._.0._.2.p.x._.v.a.r.(.-.-.g.e.i.s.t.-.b.a.c.k.g.r.o.u.n.d.).,.0._.0._.0._.4.p.x._.v.a.r.(.-.-.g.e.i.s.t.-.l.i.n.k.-.c.o.l.o.r.).]. .r.o.u.n.d.e.d.-.[.v.a.r.(.-.-.g.e.i.s.t.-.r.a.d.i.u.s.).]. .o.p.a.c.i.t.y.-.0. .p.o.i.n.t.e.r.-.e.v.e.n.t.s.-.n.o.n.e. .f.o.c.u.s.:.o.p.a.c.i.t.y.-.1.0.0. .f.o.c.u.s.:.[.p.o.i.n.t.e.r.-.e.v.e.n.t.s.:._.a.l.l.], div.z.-.[.2.0.0.1.]. .p.t.-.1, div.w.-.f.u.l.l. .h.-.f.u.l.l. .i.n.s.e.t.-.0. .f.i.x.e.d. .p.o.i.n.t.e.r.-.e.v.e.n.t.s.-.n.o.n.e. .z.-.[.1.0.0.0.0.0.] |
| dropdown | 100,100 | aside.s.h.r.i.n.k.-.0. .z.-.[.1.0.0.]. .s.t.i.c.k.y. .h.-.s.c.r.e.e.n. .t.o.p.-.0. .r.i.g.h.t.-.0. .t.r.a.n.s.i.t.i.o.n.-.t.r.a.n.s.f.o.r.m.a.t.i.o.n. .e.a.s.e.-.i.n.-.o.u.t. .t.r.a.n.s.i.t.i.o.n.-.[.w.i.d.t.h.]. .d.u.r.a.t.i.o.n.-.2.5.0. .w.-.0. .o.v.e.r.f.l.o.w.-.h.i.d.d.e.n |
| sticky | 10,76 | div.m.a.x.-.w.-.(.-.-.d.s.-.p.a.g.e.-.w.i.d.t.h.-.w.i.t.h.-.m.a.r.g.i.n.). .p.x.-.(.-.-.g.e.i.s.t.-.p.a.g.e.-.m.a.r.g.i.n.). .m.x.-.a.u.t.o. .r.e.l.a.t.i.v.e. .z.-.1.0, header.r.e.l.a.t.i.v.e. .z.-.1.0. .m.x.-.a.u.t.o. .f.l.e.x. .w.-.f.u.l.l. .m.a.x.-.w.-.[.4.4.4.p.x.]. .f.l.e.x.-.c.o.l. .i.t.e.m.s.-.c.e.n.t.e.r. .g.a.p.-.4. .t.e.x.t.-.c.e.n.t.e.r. .@.l.g.:.g.a.p.-.8. .@.l.g.:.m.x.-.0. .@.l.g.:.i.t.e.m.s.-.s.t.a.r.t. .@.l.g.:.t.e.x.t.-.l.e.f.t. .s.e.l.e.c.t.-.t.e.x.t, div.h.i.d.d.e.n. .r.e.l.a.t.i.v.e. .z.-.1.0. .w.-.f.u.l.l. .m.a.x.-.w.-.[.3.6.4.p.x.]. .t.e.x.t.-.c.e.n.t.e.r. .m.x.-.0. .@.l.g.:.b.l.o.c.k. .s.e.l.e.c.t.-.t.e.x.t |
| base | 0,2 | div.p.o.i.n.t.e.r.-.e.v.e.n.t.s.-.n.o.n.e. .z.-.0. .r.e.l.a.t.i.v.e. .f.l.e.x.-.1. .w.-.f.u.l.l. .m.i.n.-.h.-.0. .@.l.g.:.a.b.s.o.l.u.t.e. .@.l.g.:.i.n.s.e.t.-.0. .@.l.g.:.f.l.e.x.-.n.o.n.e. .@.l.g.:.w.-.a.u.t.o, div.a.b.s.o.l.u.t.e. .l.e.f.t.-.1./.2. .t.o.p.-.1./.2. .-.t.r.a.n.s.l.a.t.e.-.x.-.1./.2. .-.t.r.a.n.s.l.a.t.e.-.y.-.1./.2. .h.-.f.u.l.l. .@.l.g.:.m.a.x.-.h.-.[.v.a.r.(.-.-.h.e.r.o.-.z.o.o.m.-.f.r.e.e.z.e.-.h.).]. .a.s.p.e.c.t.-.s.q.u.a.r.e. .z.-.0. .p.o.i.n.t.e.r.-.e.v.e.n.t.s.-.n.o.n.e. .d.a.r.k.:.h.i.d.d.e.n. .s.c.a.l.e.-.[.1...6.]. .@.l.g.:.s.c.a.l.e.-.[.1...3.], div.a.b.s.o.l.u.t.e. .i.n.s.e.t.-.0. .z.-.0. .o.v.e.r.f.l.o.w.-.h.i.d.d.e.n. .p.o.i.n.t.e.r.-.e.v.e.n.t.s.-.n.o.n.e. .d.a.r.k.:.b.g.-.b.l.a.c.k |

**Issues:**
- [object Object]

## SVG Icons

**25 unique SVG icons** detected. Dominant style: **filled**.

| Size Class | Count |
|------------|-------|
| xs | 7 |
| sm | 10 |
| md | 1 |
| xl | 7 |

**Icon colors:** `currentColor`, `rgb(0, 0, 0)`, `var(--ds-background-100)`, `white`

## Font Files

| Family | Source | Weights | Styles |
|--------|--------|---------|--------|
| Roboto Mono | cdn | 400, 500, 700 | normal |
| Geist Mono | self-hosted | 100 900 | normal |
| GeistSans | self-hosted | 100 900 | normal |
| GeistPixelSquare | self-hosted | 500 | normal |
| GeistPixelGrid | self-hosted | 500 | normal |
| GeistPixelCircle | self-hosted | 500 | normal |
| GeistPixelTriangle | self-hosted | 500 | normal |
| GeistPixelLine | self-hosted | 500 | normal |

## Image Style Patterns

| Pattern | Count | Key Styles |
|---------|-------|------------|
| thumbnail | 8 | objectFit: fill, borderRadius: 0px, shape: square |
| gallery | 3 | objectFit: fill, borderRadius: 0px, shape: square |
| hero | 1 | objectFit: cover, borderRadius: 0px, shape: square |
| general | 1 | objectFit: fill, borderRadius: 0px, shape: square |

**Aspect ratios:** 16:9 (3x), 6.35:1 (1x), 1.97:1 (1x), 8.65:1 (1x), 3.71:1 (1x), 3.64:1 (1x), 4:3 (1x), 4.33:1 (1x)

## Motion Language

**Feel:** mixed · **Scroll-linked:** yes

### Duration Tokens

| name | value | ms |
|---|---|---|
| `xs` | `100ms` | 100 |
| `sm` | `200ms` | 200 |
| `md` | `300ms` | 300 |
| `lg` | `500ms` | 500 |
| `xl` | `1s` | 1000 |

### Easing Families

- **custom** (144 uses) — `cubic-bezier(0.4, 0, 0.2, 1)`
- **linear** (2 uses) — `linear`
- **ease-out** (17 uses) — `cubic-bezier(0, 0, 0.2, 1)`, `cubic-bezier(0.32, 0.72, 0, 1)`, `cubic-bezier(0.23, 1, 0.32, 1)`

### Keyframes In Use

| name | kind | properties | uses |
|---|---|---|---|
| `fade-in` | fade | opacity | 2 |
| `marquee` | slide | transform | 2 |

## Component Anatomy

### button — 11 instances

**Slots:** label, icon
**Variants:** outline
**Sizes:** md · sm

| variant | count | sample label |
|---|---|---|
| default | 6 |  |
| outline | 5 | Products |

## Brand Voice

**Tone:** neutral · **Pronoun:** you-only · **Headings:** Sentence case (tight)

### Top CTA Verbs

- **products** (1)
- **resources** (1)
- **plugin** (1)
- **cookie** (1)

### Button Copy Patterns

- "products" (1×)
- "resources" (1×)
- "plugin" (1×)
- "cookie preferences" (1×)

### Sample Headings

> Agent Stack
> Core Platform
> Tools
> Learn
> Build
> Agentic Infrastructure
> Build agents on infrastructure that thinks like them
> Host platforms that serve every customer
> Recently shipped
> Agentic Infrastructure

## Page Intent

**Type:** `landing` (confidence 0.29)
**Description:** The autonomous stack for every app and agent.

Alternates: legal (0.4), blog-post (0.35)

## Section Roles

Reading order (top→bottom): feature-grid → content → nav → nav → feature-grid → content → content → testimonials → content → content → feature-grid → nav → cta → nav → sidebar → nav → nav → content → content → footer → nav

| # | Role | Heading | Confidence |
|---|------|---------|------------|
| 0 | cta | Agent Stack | 0.75 |
| 1 | nav | — | 0.9 |
| 2 | feature-grid | Agentic Infrastructure | 0.8 |
| 3 | content | Agentic Infrastructure | 0.3 |
| 4 | nav | Agentic Infrastructure | 0.4 |
| 5 | nav | — | 0.9 |
| 6 | feature-grid | Build agents on infrastructure that thinks like them | 0.8 |
| 7 | content | Build agents on infrastructure that thinks like them | 0.3 |
| 8 | content | — | 0.3 |
| 9 | testimonials | Host platforms that serve every customer | 0.4 |
| 10 | content | Recently shipped | 0.3 |
| 11 | content | Recently shipped | 0.3 |
| 12 | feature-grid | — | 0.8 |
| 13 | nav | — | 0.4 |
| 14 | nav | — | 0.4 |
| 15 | nav | — | 0.4 |
| 16 | content | Built by you, or your agents | 0.3 |
| 17 | content | Built by you, or your agents | 0.3 |
| 18 | footer | Agent Stack | 0.95 |
| 19 | nav | Agent Stack | 0.9 |

## Material Language

**Label:** `flat` (confidence 0)

| Metric | Value |
|--------|-------|
| Avg saturation | 0.091 |
| Shadow profile | soft |
| Avg shadow blur | 0px |
| Max radius | 12px |
| backdrop-filter in use | no |
| Gradients | 7 |

## Imagery Style

**Label:** `gradient-mesh` (confidence 0.513)
**Counts:** total 13, svg 9, icon 1, screenshot-like 0, photo-like 3
**Dominant aspect:** ultra-wide
**Radius profile on images:** square

## Component Library

**Detected:** `shadcn/ui` (confidence 0.65)

Evidence:
- shadcn css tokens

Also considered: tailwindcss (0.3)

## Component Screenshots

4 retina crops written to `screenshots/`. Index: `*-screenshots.json`.

| Cluster | Variant | Size (px) | File |
|---------|---------|-----------|------|
| button--outline | 0 | 94 × 32 | `screenshots/button-outline-0.png` |
| button--outline | 1 | 104 × 32 | `screenshots/button-outline-1.png` |
| button--outline | 2 | 28 × 28 | `screenshots/button-outline-2.png` |
| button--outline--md | 0 | 107 × 32 | `screenshots/button-outline-md-0.png` |

Full-page: `screenshots/full-page.png`

## Quick Start

To recreate this design in a new project:

1. **Install fonts:** Add `GeistSans` from Google Fonts or your font provider
2. **Import CSS variables:** Copy `variables.css` into your project
3. **Tailwind users:** Use the generated `tailwind.config.js` to extend your theme
4. **Design tokens:** Import `design-tokens.json` for tooling integration
