---
name: fintrixa-design-system
description: Use when implementing or modifying frontend/ — the lavender/white/black design system tokens (color, type, spacing) and the semantic-signal color exception for Buy/Hold/Avoid. Every component must use these tokens, not ad-hoc values.
---

# Fintrixa Design System

Brand palette is lavender, white, and black — stable, calm, not another
green-red trading-app cliché. One deliberate exception: Buy/Hold/Avoid
signal colors (see below) — documented in `docs/DECISIONS.md`, flag to
the user if this should be removed in favor of strict 3-color purity.

## Implementation: Tailwind CSS v4, not inline styles

Tokens below live in `frontend/src/styles/globals.css` as a Tailwind v4
`@theme` block (`--color-lavender-500` etc.), which auto-generates
utility classes (`bg-lavender-500`, `text-lavender-700`, ...). Use those
utility classes on components — never hand-roll inline `style={{...}}`
objects or hardcoded hex values. Shared primitives live in
`frontend/src/components/ui/` (Table, Badge, Card, Skeleton, Alert),
styled with `class-variance-authority` for variants and the `cn()`
helper (`frontend/src/lib/utils.ts`) for merging classes — this is a
shadcn/ui-style copy-paste component approach, not a runtime UI library
dependency. Build new components out of these primitives instead of
raw `<div>`/`<table>` elements with inline styles.

**Known gotcha:** after `npm install`, verify the Tailwind build
actually produced real CSS output before considering a UI task done —
`npm run build` and check `dist/assets/*.css` is more than a few hundred
bytes (a near-empty CSS file means the `@tailwindcss/vite` plugin isn't
wired into `vite.config.ts`, or `globals.css` isn't imported through
`main.tsx`). This has silently broken once already; don't trust that
"the build succeeded" means styles actually rendered — Vite won't error
just because Tailwind generated nothing.

## Color tokens

```css
--lavender-50:  #F5F2FB;  /* faint tint, backgrounds */
--lavender-100: #E8E1F5;  /* hover/subtle surfaces */
--lavender-300: #C3AFE8;  /* secondary accents */
--lavender-500: #8E6FD1;  /* primary brand — buttons, links, active states */
--lavender-700: #5F45A3;  /* primary hover/pressed */
--lavender-900: #362566;  /* deep accent, dark-mode primary surfaces */

--white:        #FFFFFF;
--off-white:    #FAF9FC;  /* app background, light mode */

--black:        #0B0A0F;  /* app background, dark mode */
--ink-900:      #17151F;  /* primary text, light mode */
--ink-600:      #4B4759;  /* secondary text */
--ink-400:      #85809A;  /* tertiary text, placeholders */
--border:       #E3DEEE;  /* light mode hairlines */
--border-dark:  #2B2735;  /* dark mode hairlines */
```

## Semantic signal exception

Financial-verdict colors are the one place semantic clarity outranks
palette purity — a layman must recognize Buy vs Avoid instantly, and
lavender-only shading is too subtle for that safety-critical read:

```css
--signal-strong-buy: #2F9E63;  /* green, use sparingly — tag/badge only */
--signal-buy:        #6FB98F;  /* muted green */
--signal-hold:        var(--lavender-300);  /* stays in-palette */
--signal-avoid:       #C1473B;  /* red, use sparingly — tag/badge only */
```

Signal colors appear only on verdict badges/tags, never as large fills,
backgrounds, or chrome — everything else (nav, cards, buttons, charts'
non-signal elements) stays lavender/white/black.

## Type scale

- Font: system UI stack (`-apple-system, "Segoe UI", Inter, sans-serif`)
  — no external font loading dependency for a local-only MVP.
- Scale: 12 / 14 / 16 / 20 / 24 / 32 px, 1.4 line-height for body, 1.2
  for headings.

## Spacing

4px base unit: 4 / 8 / 12 / 16 / 24 / 32 / 48.

## Components

- **Verdict badge**: signal color background at 15% opacity, signal
  color text/border, label + score.
- **Ranked table**: lavender-100 header row, hairline row borders,
  hover = lavender-50 (light) / lavender-900 at low opacity (dark).
- **Cards**: white/black surface, 1px border, 8px radius, no heavy
  shadows — flat and calm, not skeuomorphic.
- **Charts**: lavender-500 as the primary price line; signal colors only
  for verdict-change markers, never the whole line.

## Dark mode

Support both light and dark — `off-white`/`ink-900` background/text in
light, `black`/`white` in dark, lavender scale flips toward
`lavender-300`/`lavender-500` for accents in dark mode (better contrast
on black than the darker shades). Respect `prefers-color-scheme` by
default; allow manual toggle.

## Accessibility

Verify contrast ratios explicitly (WCAG AA, 4.5:1 body text) — a
constrained 3-color-plus-signal palette makes it easy to accidentally
ship low-contrast text. Don't rely on color alone for verdict meaning —
always pair with the text label.
