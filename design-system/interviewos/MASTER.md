# InterviewOS design system (MASTER)

Coaching SaaS for high-stakes interview practice. Swiss / minimal surfaces with a dark interview stage. Not a kids LMS and not a terminal-green coding theme.

## Tokens

| Role | Value | Notes |
|---|---|---|
| Primary | `#1E3A8A` | Authority navy |
| On primary | `#FFFFFF` | |
| Accent / CTA | `#B45309` | Trust gold |
| On accent | `#FFFFFF` | Contrast ≥ 4.5:1 |
| Background | `#F8FAFC` | Off-white, not pure white |
| Foreground | `#0F172A` | |
| Card | `#FFFFFF` | |
| Muted | `#E9EEF5` | |
| Muted foreground | `#475569` | |
| Border | `#CBD5E1` | Visible in light |
| Interview room bg | `#0F172A` | Dark stage only |
| Interview room fg | `#F8FAFC` | |
| Destructive | `#DC2626` | |
| Ring | `#1E3A8A` | Visible focus, 2px offset |

## Typography

- Family: Inter (300–700)
- One family only
- Heading tracking slightly tight; body 16px / 1.5
- Long-form measure: max ~65ch

## Layout

- Landing / setup / report: 12-column grid, max width 1120px, spacious
- Interview room: full viewport, no marketing chrome, no ethics essay
- Report dashboard: denser (8–16px rhythm)

## Motion

- 1 presence animation in the interview room (slow opacity pulse)
- Hover 150–250ms color/opacity only
- `@media (prefers-reduced-motion: reduce)`: no infinite animation; jump to rest state
- Infinite motion only for loading indicators

## Icons

- Phosphor outline, regular weight, 20px default
- No emoji as structural icons
- Icon-only buttons need `aria-label`

## Charts

- Qualitative rubric: horizontal bars (≤8 axes)
- Technical: KPI bullets + text
- Always a data table fallback
- Do not use a 10-axis radar

## Components

- shadcn-style Field + FieldLabel + Control
- Never placeholder-as-only-label
- Failed submit: focusable error summary at top (`role="alert"`, `tabIndex={-1}`) plus inline `aria-describedby`
- Loading: skeleton / `aria-busy`, no layout jump

## Landing

Hero + 3–5 features + CTA, then “Start practice”. Sticky header CTA allowed; no form buried in pitch.

## Anti-patterns

- Marketing copy during the live interview
- CSS smiley avatars with blink/float loops
- Hardcoded `bg-blue-500`
- Claymorphism / playful LMS pastels
- OLED code-green
