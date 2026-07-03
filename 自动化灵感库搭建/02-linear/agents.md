# Agent instructions — design system

This project follows the design system extracted from https://linear.app.
Any coding agent working here must use the tokens below and avoid inventing new ones.
Source: https://linear.app
Extracted by designlang v7.0.0 on 2026-07-02T08:20:32.913Z

## Semantic tokens (use these)
- color.action.primary: #e4f222
- color.surface.default: #08090a
- color.text.body: #f7f8f8
- radius.control: 1px
- typography.body.fontFamily: Inter Variable

## Regions
- content
- nav
- nav
- testimonials
- nav
- nav
- nav
- content
- testimonials
- nav
- testimonials
- nav
- hero
- nav
- testimonials
- hero
- nav
- nav
- nav
- testimonials
- content
- footer

## How to use
- Prefer `semantic.*` tokens over `primitive.*`.
- Never invent new tokens or hex values; reuse the ones above.
- When a value is missing, pick the closest existing semantic token and flag the gap.
- Reference tokens by their dotted path (e.g. `semantic.color.action.primary`).
