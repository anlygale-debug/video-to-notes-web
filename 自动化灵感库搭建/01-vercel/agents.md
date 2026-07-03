# Agent instructions — design system

This project follows the design system extracted from https://vercel.com.
Any coding agent working here must use the tokens below and avoid inventing new ones.
Source: https://vercel.com
Extracted by designlang v7.0.0 on 2026-07-02T04:38:03.262Z

## Semantic tokens (use these)
- color.action.primary: #0070f3
- color.surface.default: #fafafa
- color.text.body: #171717
- radius.control: 2px
- typography.body.fontFamily: GeistSans

## Regions
- nav
- nav
- testimonials
- content
- nav
- nav
- testimonials
- content
- content
- testimonials
- content
- content
- features
- nav
- nav
- nav
- content
- content
- footer
- nav
- sidebar

## How to use
- Prefer `semantic.*` tokens over `primitive.*`.
- Never invent new tokens or hex values; reuse the ones above.
- When a value is missing, pick the closest existing semantic token and flag the gap.
- Reference tokens by their dotted path (e.g. `semantic.color.action.primary`).
