# Design System

Complete reference for the A-Stats-Online visual design system — colors, typography, components, tokens, animations, and utility classes.

**Source files:**
- `frontend/tailwind.config.ts` — Tailwind theme extensions
- `frontend/app/globals.css` — CSS variables, base styles, component classes, utilities

---

## Table of Contents

1. [Color Palette](#color-palette)
2. [Typography](#typography)
3. [Component Styles](#component-styles)
4. [Design Tokens](#design-tokens)
5. [Animations](#animations)
6. [Shadows](#shadows)
7. [Border Radius](#border-radius)
8. [Utility Classes](#utility-classes)

---

## Color Palette

### Primary — Sage Green

The brand identity color. Used for buttons, links, focus rings, and accent elements.

| Token | Hex | Usage |
|-------|-----|-------|
| `primary-50` | `#f6f7f6` | Lightest tint, hover backgrounds |
| `primary-100` | `#e3e7e3` | Light backgrounds |
| `primary-200` | `#c7d0c7` | Borders, dividers |
| `primary-300` | `#a3b2a3` | Disabled states |
| `primary-400` | `#7d917d` | Secondary text on light |
| `primary-500` | `#627862` | **Main brand color** — buttons, links |
| `primary-600` | `#4d5f4d` | Hover state for primary buttons |
| `primary-700` | `#404d40` | Active/pressed states |
| `primary-800` | `#363f36` | Dark accents |
| `primary-900` | `#2e352e` | Matches text-primary |
| `primary-950` | `#171c17` | Darkest shade |

### Surface — Warm Cream

Background surfaces throughout the application. **Never use `bg-white` or `gray-*` in the dashboard.**

| Token | Hex | Usage |
|-------|-----|-------|
| `surface` (DEFAULT) | `#fdfcfa` | Page background, card backgrounds |
| `surface-secondary` | `#f9f6f0` | Elevated sections, hover states |
| `surface-tertiary` | `#f3ece0` | Borders, dividers, input backgrounds |

### Text

| Token | Hex | Usage |
|-------|-----|-------|
| `text-primary` | `#2e352e` | Body text, headings |
| `text-secondary` | `#533f38` | Subtitles, descriptions |
| `text-muted` | `#6c5b45` | Placeholders, helper text |
| `text-tertiary` | `#9b8e7b` | Timestamps, metadata |

### Extended Scales

#### Cream (warm neutrals)

| Token | Hex |
|-------|-----|
| `cream-50` | `#fdfcfa` |
| `cream-100` | `#f9f6f0` |
| `cream-200` | `#f3ece0` |
| `cream-300` | `#e9dcc8` |
| `cream-400` | `#dcc8a8` |
| `cream-500` | `#cfb48d` |

#### Earth (brown accent)

| Token | Hex |
|-------|-----|
| `earth-400` | `#b29581` |
| `earth-500` | `#a17d66` |
| `earth-600` | `#946c5a` |
| `earth-700` | `#7b594c` |
| `earth-800` | `#654a42` |

#### Terra (warm orange-brown accent)

| Token | Hex |
|-------|-----|
| `terra-400` | `#cb9379` |
| `terra-500` | `#bc7a5c` |
| `terra-600` | `#ae6850` |
| `terra-700` | `#915544` |
| `terra-800` | `#77483c` |

### Healing (semantic aliases)

Named color aliases for semantic use:

| Token | Hex | Maps to |
|-------|-----|---------|
| `healing-sage` | `#627862` | primary-500 |
| `healing-lavender` | `#a17d66` | earth-500 |
| `healing-sky` | `#bc7a5c` | terra-500 |
| `healing-sand` | `#e9dcc8` | cream-300 |
| `healing-cream` | `#fdfcfa` | surface DEFAULT |

### Social Platform Colors

| Token | Hex | Platform |
|-------|-----|----------|
| `social-twitter` | `#1DA1F2` | Twitter/X |
| `social-linkedin` | `#0A66C2` | LinkedIn |
| `social-facebook` | `#1877F2` | Facebook |
| `social-instagram` | `#E4405F` | Instagram |
| `social-wordpress` | `#21759B` | WordPress |

### CSS Variable Colors (shadcn/ui compatibility)

HSL-based variables defined in `:root` for shadcn/ui components. Referenced via `hsl(var(--name))` in Tailwind config.

| Variable | HSL Value | Purpose |
|----------|-----------|---------|
| `--background` | `40 40% 98%` | Page background |
| `--foreground` | `138 10% 19%` | Default text |
| `--card` | `40 40% 98%` | Card background |
| `--card-foreground` | `138 10% 19%` | Card text |
| `--popover` | `40 40% 98%` | Popover background |
| `--popover-foreground` | `138 10% 19%` | Popover text |
| `--primary` | `138 20% 42%` | Primary actions |
| `--primary-foreground` | `40 40% 98%` | Text on primary |
| `--secondary` | `38 30% 88%` | Secondary actions |
| `--secondary-foreground` | `138 10% 19%` | Text on secondary |
| `--muted` | `38 30% 88%` | Muted backgrounds |
| `--muted-foreground` | `30 20% 35%` | Muted text |
| `--accent` | `14 40% 55%` | Accent highlights |
| `--accent-foreground` | `40 40% 98%` | Text on accent |
| `--destructive` | `0 65% 50%` | Destructive actions |
| `--destructive-foreground` | `40 40% 98%` | Text on destructive |
| `--border` | `36 15% 86%` | Default borders |
| `--input` | `36 15% 86%` | Input borders |
| `--ring` | `138 20% 42%` | Focus rings |
| `--radius` | `0.75rem` | Default border radius |

Tailwind references these as:
- `border` — `hsl(var(--border))`
- `input` — `hsl(var(--input))`
- `ring` — `hsl(var(--ring))`
- `background` — `hsl(var(--background))`
- `foreground` — `hsl(var(--foreground))`

---

## Typography

### Font Families

| Token | Stack | Usage |
|-------|-------|-------|
| `font-sans` | Source Sans 3, Inter, system-ui, sans-serif | Body text, UI elements |
| `font-display` | Playfair Display, Cal Sans, Georgia, serif | Headings (h1-h6) |

### Base Heading Styles

All headings (`h1`-`h6`) apply `font-display tracking-tight` globally.

| Element | Size (mobile) | Size (sm+) |
|---------|---------------|------------|
| `h1` | `text-2xl` (1.5rem) | `text-3xl` (1.875rem) |
| `h2` | `text-xl` (1.25rem) | `text-2xl` (1.5rem) |

### Body

```css
body {
  @apply bg-surface text-text-primary antialiased;
  font-feature-settings: "rlig" 1, "calt" 1;
}
```

OpenType features `rlig` (required ligatures) and `calt` (contextual alternates) are enabled for improved text rendering.

---

## Component Styles

Defined as Tailwind `@layer components` classes in `globals.css`.

### Buttons

**Base class `.btn`:**
```
inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-medium
transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
disabled:opacity-50 disabled:pointer-events-none
```

| Class | Background | Text | Hover | Focus Ring |
|-------|-----------|------|-------|------------|
| `.btn-primary` | `primary-500` | white | `primary-600` | `primary-500` |
| `.btn-secondary` | `surface-secondary` | `text-primary` | `surface-tertiary` | `primary-500` |
| `.btn-ghost` | transparent | inherited | `surface-secondary` | `primary-500` |

Additional button variants exist as React components (`Button` in `components/ui/button.tsx`) with variants: `primary`, `secondary`, `ghost`, `outline`, `destructive`, `link`.

### Cards

**Class `.card`:**
```
bg-surface rounded-2xl border border-surface-tertiary shadow-soft
```

### Gradient Text

**Class `.gradient-text`:**
```
bg-gradient-to-r from-primary-500 to-terra-500 bg-clip-text text-transparent
```

Creates a sage-to-terra horizontal gradient on text.

### Page Container

**Class `.page-container`:**
```
mx-auto max-w-7xl px-4 sm:px-6 lg:px-8
```

Standard centered container with responsive horizontal padding.

---

## Design Tokens

### Spacing

Standard Tailwind spacing scale. No custom overrides.

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `rounded-soft` | `0.625rem` (10px) | Input fields, small elements |
| `rounded-softer` | `1rem` (16px) | Cards, modals |
| `rounded-4xl` | `2rem` (32px) | Large pills, hero elements |
| `rounded-xl` | `0.75rem` | Buttons (from base `.btn`) |
| `rounded-2xl` | `1rem` | Cards (from `.card` class) |
| `--radius` | `0.75rem` | shadcn/ui default radius |

---

## Shadows

Custom shadows use the primary-900 color (`rgba(46, 53, 46, ...)`) for a warm, natural tone instead of pure black.

| Token | Value | Usage |
|-------|-------|-------|
| `shadow-soft` | `0 2px 8px -2px rgba(46,53,46,0.08), 0 4px 16px -4px rgba(46,53,46,0.12)` | Cards, elevated surfaces |
| `shadow-soft-lg` | `0 4px 12px -4px rgba(46,53,46,0.1), 0 8px 24px -8px rgba(46,53,46,0.15)` | Modals, dropdowns, popovers |
| `shadow-inner-soft` | `inset 0 2px 4px 0 rgba(46,53,46,0.05)` | Pressed/inset states |

---

## Animations

### Tailwind Animations (via `animate-*`)

| Class | Duration | Easing | Behavior | Usage |
|-------|----------|--------|----------|-------|
| `animate-fade-in` | 0.3s | ease-in-out | Once | General entrance |
| `animate-slide-up` | 0.4s | ease-out | Once | Content appearing from below |
| `animate-pulse-soft` | 2s | ease-in-out | Infinite | Loading states, skeleton |
| `animate-writing` | 1.5s | ease-in-out | Infinite | Writing/generating indicator |

### Keyframe Details

**fadeIn:** `opacity: 0 -> 1`

**slideUp:** `translateY(10px) + opacity: 0 -> translateY(0) + opacity: 1`

**pulseSoft:** `opacity: 1 -> 0.7 -> 1` (infinite cycle)

**writing:** Pen-like motion — `rotate(-5deg) -> rotate(0deg) translateY(-2px) -> rotate(5deg) -> rotate(0deg) translateY(2px)` (infinite cycle)

---

## Utility Classes

### `.animate-in`

Quick entrance animation. `translateY(8px) + opacity: 0` to rest position over 0.3s.

### Scroll Reveal System

For landing page scroll-triggered animations using IntersectionObserver.

| Class | Direction | Distance | Duration |
|-------|-----------|----------|----------|
| `.scroll-reveal` | Vertical (up) | 24px | 0.7s |
| `.scroll-reveal-left` | Horizontal (left) | 32px | 0.7s |
| `.scroll-reveal-right` | Horizontal (right) | 32px | 0.7s |

Add `.revealed` class via JavaScript to trigger the animation.

**Stagger children:** Elements with `.stagger-child` inside a `.scroll-reveal.revealed` parent animate sequentially:
- Child 1: 0.05s delay
- Child 2: 0.1s delay
- Child 3: 0.15s delay
- Child 4: 0.2s delay
- Child 5: 0.25s delay
- Child 6: 0.3s delay

### Hero Animations

For landing page hero section. `translateY(20px) + opacity: 0` to rest over 0.8s.

| Class | Delay |
|-------|-------|
| `.hero-animate` | 0s (immediate) |
| `.hero-animate-delay-1` | 0.15s |
| `.hero-animate-delay-2` | 0.3s |
| `.hero-animate-delay-3` | 0.45s |

### FAQ Accordion

Styles for `<details>` / `<summary>` based FAQ sections:

- `.faq-item summary` — Hides default marker/disclosure triangle
- `.faq-item[open] .faq-icon` — Rotates icon 45 degrees when open
- `.faq-item[open] .faq-answer` — Animates answer in (0.3s, slides down 8px)

### Scrollbar Utilities

| Class | Effect |
|-------|--------|
| `.scrollbar-hide` | Completely hides scrollbars (all browsers) |
| `.scrollbar-sidebar` | Thin 4px scrollbar with translucent white thumb, for dark sidebar backgrounds |

### LemonSqueezy Overlay

```css
.lemonsqueezy-loader {
  background: rgba(0, 0, 0, 0.4) !important;
  backdrop-filter: blur(4px);
}
```

Overrides the default LemonSqueezy checkout overlay backdrop to use 40% opacity with a 4px blur effect.

---

## Design Rules

1. **No `bg-white` in dashboard** — Use `bg-surface`, `bg-surface-secondary`, or `bg-surface-tertiary`
2. **No `gray-*` in dashboard** — Use the cream/surface/text token scales
3. **Shadows use sage-tinted rgba** — Never pure black shadows
4. **Headings always use `font-display`** — Applied globally via base styles
5. **Focus rings use `ring-primary-500`** — Consistent accessibility indicator
6. **Button min touch target: 44px** — Enforced in interactive components
7. **`@tailwindcss/typography` plugin** — Available for prose content (blog posts, articles)
