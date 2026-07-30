# AccentIQ Design System

## Overview

This document is the canonical reference for AccentIQ's visual design. Every frontend change must use these tokens and components — no hand-rolled one-off styling.

## Color Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | `#991B1B` | CTAs, links, active states, badges |
| `--color-primary-hover` | `#7F1D1D` | Hover states on primary elements |
| `--color-primary-soft` | `#FEF2F2` | Tint backgrounds for pills/badges |
| `--color-secondary` | `#B91C1C` | Emphasis, secondary CTAs |
| `--color-bg` | `#FFFFFF` | Page background |
| `--color-bg-soft` | `#F5F7FF` | Section wash, card backgrounds |
| `--color-ink` | `#111827` | Primary text |
| `--color-ink-muted` | `#6B7280` | Secondary/description text |
| `--color-ink-faint` | `#9CA3AF` | Timestamps, metadata |
| `--color-border` | `#E5E9FF` | Card/input borders |

## Typography

| Scale | Classes | Usage |
|-------|---------|-------|
| Hero | `text-5xl font-display font-extrabold tracking-tight` | Landing page hero |
| H1 | `text-2xl font-display font-bold` | Page titles |
| H2 | `text-xl font-display font-bold` | Section headings |
| Body | `text-base text-ink-muted` | Paragraph text |
| Micro | `text-xs font-display font-semibold uppercase tracking-wider text-primary` | Labels |

**Fonts:**
- Display: Plus Jakarta Sans (headings, buttons)
- Body: Inter (text, descriptions)
- Mono: IBM Plex Mono (code, phonemes)

## Spacing & Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 8px | Inputs, small pills |
| `--radius-md` | 12px | Buttons, cards |
| `--radius-lg` | 16px | Large cards |
| `--radius-xl` | 20px | Modals |
| `--radius-pill` | 999px | Fully rounded pills |
| Section spacing | `py-16` | Between major sections |
| Card gap | `gap-6` | Grid card spacing |

## Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 2px 8px rgba(153,27,27,0.04)` | Subtle card |
| `--shadow-md` | `0 4px 24px rgba(153,27,27,0.06)` | Elevated/hover |
| `--shadow-lg` | `0 8px 32px rgba(153,27,27,0.08)` | Modals |

## Shared Components

### `<IconBadge icon="🎯" size="md" color="primary" />`

Circular pastel-tint icon badge.

| Prop | Type | Default | Options |
|------|------|---------|---------|
| icon | string | required | Any emoji/text |
| size | string | "md" | "sm" \| "md" \| "lg" |
| color | string | "primary" | "primary" \| "secondary" \| "muted" |

---

### `<StepCard step={1} icon="⬆️" title="Upload" description="..." />`

Step indicator card with number label + icon + title + description.

| Prop | Type | Default |
|------|------|---------|
| step | number | required |
| icon | string | required |
| title | string | required |
| description | string | required |

---

### `<FeatureCard icon="🎯" label="Core" title="..." description="..." />`

Feature grid card with category pill.

| Prop | Type | Default |
|------|------|---------|
| icon | string | required |
| label | string | required |
| title | string | required |
| description | string | required |
| labelColor | string | "primary" |

---

### `<PrimaryButton onClick={fn} loading={false} fullWidth={true}>Text</PrimaryButton>`

Full-width maroon gradient CTA button.

| Prop | Type | Default |
|------|------|---------|
| children | ReactNode | required |
| disabled | boolean | false |
| loading | boolean | false |
| fullWidth | boolean | true |
| type | string | "button" |
| onClick | function | — |

---

### `<Modal isOpen={true} onClose={fn} title="Sign In">...</Modal>`

Shared modal shell with backdrop blur + escape-to-close.

| Prop | Type | Default |
|------|------|---------|
| isOpen | boolean | required |
| onClose | function | required |
| title | string | — |
| children | ReactNode | required |
| maxWidth | string | "md" |

---

### `<DropZone onDrop={fn} onClick={fn}>...</DropZone>`

Dashed-border upload/drag area.

| Prop | Type | Default |
|------|------|---------|
| onDrop | function | — |
| onClick | function | — |
| active | boolean | — |
| children | ReactNode | required |

---

### `<MicroLabel text="STEP 1" color="primary" />`

Small-caps letter-spaced accent label.

| Prop | Type | Default |
|------|------|---------|
| text | string | required |
| color | string | "primary" |

---

### `<FooterColumn title="Product" items={["Upload", "AI Coaching"]} />`

Reusable footer link column.

| Prop | Type | Default |
|------|------|---------|
| title | string | required |
| items | string[] | [] |

## CSS Utility Classes

Pre-built in `index.css`:
- `.btn-primary` — Gradient maroon button
- `.btn-secondary` — Outlined button
- `.btn-ghost` — Transparent button
- `.card` — Standard card (border + shadow + radius)
- `.card-hover` — Card with hover elevation
- `.card-soft` — Soft background card (no border)
- `.pill` — Base pill styling
- `.pill-blue`, `.pill-purple`, `.pill-success`, etc.

## Usage Rules

1. **Always use tokens** — never hardcode hex colors or pixel values
2. **Always use shared components** — never duplicate a pattern that exists here
3. **Extend, don't override** — if you need a variant, add a prop, don't create a new component
4. **Document additions** — if you add a new component, add its props table here

---

*Design System v1.0 | Phase 34 | Last updated: 2026-07-31*
