# Component Spec – Logos Ask (v2)

## Overview
This spec documents **only** the visual layer of the `logos-research-ask-page` surface. All class names, `data-*` attributes and DOM hierarchy remain **unchanged**. The spec focuses on the seven pins (S4 accordion, citation‑lock strip, report‑split & graph chrome, composer, onboarding, streaming/error, responsive frames) and defines the visual states, token mappings, and micro‑interactions.

---
### 1. S4 Accordion (Pin 1)
| Element | Class / Selector | Default | Open | Streaming Highlight |
|---------|------------------|---------|------|---------------------|
| Container | `.lr-ask-s4-sections` | `display:flex; flex-direction:column; gap:var(--space-md);` | – | – |
| Section | `.lr-ask-s4-section` | `background:rgba(255,255,255,0.72); border:1px solid var(--lr-line); border-radius:var(--radius-md); padding:var(--space-sm) var(--space-md);` | `background:rgba(255,255,255,0.88); border-color:var(--lr-accent);` | `border-left:4px solid var(--lr-accent);` |
| Title | `.lr-ask-s4-section-title` | `font-size:var(--text-sm); font-weight:700; color:var(--lr-ink); letter-spacing:-0.01em;` | same | same |
| Body | `.lr-ask-s4-section-body` | `font-size:var(--text-sm); line-height:1.65; color:var(--lr-ink-soft);` | same | same |
| Chevron (pseudo) | `.lr-ask-s4-section::after` | `content:"▸"; color:var(--lr-muted); margin-left:auto;` | `transform:rotate(90deg);` | – |
| Index badge | `.lr-ask-s4-section-index` (new span) | `background:var(--lr-accent); color:#fff; border-radius:var(--radius-sm); padding:0 var(--space-xs); font-size:var(--text-xs);` | – | – |

**Token mapping**
- `--lr-accent` → `color.logos.ask.accent` (`#2d7a68`)
- `--lr-ink` → `color.logos.ask.ink` (`#292524`)
- `--lr-ink-soft` → `color.logos.ask.ink-soft` (`#57534e`)
- Spacing uses existing `--space-*` tokens.
- Radius uses `--radius-md`.

---
### 2. Citation‑Lock Strip (Pin 2)
| Element | Selector | Visual | Interaction |
|---------|----------|--------|-------------|
| Wrapper | `.lr-ask-citation-lock` | `background:rgba(45,122,104,0.12); border:1px solid var(--lr-accent); border-radius:var(--radius-sm); padding:var(--space-xs) var(--space-sm); display:flex; gap:var(--space-xs); align-items:center;` | Hover → `background:rgba(45,122,104,0.18);` |
| Verse chip | `.lr-ask-citation-lock-ref-chip` | `background:var(--lr-accent); color:#fff; border-radius:var(--radius-pill); padding:0 var(--space-xs); font-size:var(--text-xs);` | Focus → outline `2px solid var(--lr-gold)` |
| Badge `[NON_GATING]` | `.lr-ask-citation-lock-badge` | `font-size:var(--text-xs); color:var(--lr-ink-soft);` | – |

**Token mapping**
- `--lr-accent` → teal token
- `--lr-gold` → `color.logos.ask.gold` (`#c5a057`)

---
### 3. Report Split & Graph Panel (Pin 3)
| Element | Selector | Layout (desktop) | Layout (mobile) |
|---------|----------|------------------|-----------------|
| Split container | `.lr-ask-report-split` | `display:flex; flex-direction:row; gap:var(--space-lg); align-items:flex-start;` | `flex-direction:column;` |
| Primary report | `.lr-ask-report-primary` | `flex:1 1 58%; min-width:0;` | `width:100%;` |
| Graph panel | `.lr-ask-graph-panel` | `flex:0 1 42%; min-width:280px; max-width:420px; position:sticky; top:var(--space-sm);` | `order:2; border-top:1px solid var(--lr-line); padding-top:var(--space-md);` |
| Viz toggle button | `.lr-ask-graph-viz-btn` | `background:transparent; border:none; font-size:var(--text-xs); color:var(--lr-muted);` | same |
| Active button | `.lr-ask-graph-viz-btn--active` | `background:rgba(45,122,104,0.12); color:var(--lr-navy); font-weight:600;` | – |

**Token mapping**
- Panel background → `rgba(250,247,242,0.85)` (derived from `--lr-surface`)
- Border color → `var(--lr-line)`
- Accent for active toggle → teal token.

---
### 4. Composer & Sample Chips (Pin 4)
| Element | Selector | Visual |
|---------|----------|--------|
| Composer wrapper | `.lr-ask-composer` (sticky bottom on mobile) | `position:sticky; bottom:0; background:rgba(255,255,255,0.9); padding:var(--space-sm); border-top:1px solid var(--lr-line);` |
| Textarea | `.lr-ask-input` | `border:1px solid var(--lr-line); border-radius:var(--radius-md); padding:var(--space-xs); font-size:var(--text-sm);` |
| Primary CTA | `.lr-btn-primary` | `background:var(--lr-accent); color:#fff; border:none; border-radius:var(--radius-sm); padding:var(--space-xs) var(--space-sm);` |
| Sample chip | `.lr-ask-sample-chip` | `background:var(--lr-accent); color:#fff; border-radius:var(--radius-pill); padding:0 var(--space-xs); font-size:var(--text-xs);` |
| Disabled state (running) | `.lr-ask-input[disabled]`, `.lr-btn-primary[disabled]` | `opacity:0.55; cursor:not-allowed;` |
| Focus ring | `:focus-visible` on textarea & button | `outline:2px solid rgba(45,122,104,0.4); outline-offset:1px;` |

---
### 5. Onboarding Empty State (Pin 5)
| Element | Selector | Visual |
|---------|----------|--------|
| Wrapper | `.lr-ask-onboarding` | `max-width:48rem; margin:auto; padding:var(--space-lg);` |
| Stepper (desktop) | `.lr-ask-onboarding-steps` | `display:flex; gap:var(--space-sm); justify-content:center;` |
| Step card | `.lr-ask-onboarding-step` | `background:rgba(255,255,255,0.8); border:1px solid var(--lr-line); border-radius:var(--radius-md); padding:var(--space-sm) var(--space-md); text-align:center;` |
| Sample pill (scriptorium) | `.lr-ask-onboarding-pillar` | `background:var(--lr-accent); color:#fff; border-radius:var(--radius-pill); padding:0 var(--space-xs); font-size:var(--text-xs);` |
| Dismiss button | `.lr-ask-onboarding-dismiss` | `background:none; border:none; color:var(--lr-muted); font-size:var(--text-xs);` |

---
### 6. Streaming & Error States (Pin 6)
| Element | Selector | Streaming | Error |
|---------|----------|-----------|-------|
| Bubble | `.lr-ask-bubble--summary` (inside `.lr-ask-turn--streaming`) | `animation:lr-ask-pulse 1.4s ease-in-out infinite; opacity:0.92;` | – |
| S4 section (streaming) | `.lr-ask-s4-section--streaming` | `border-left:4px solid var(--lr-accent);` | – |
| Error bubble | `.lr-ask-turn--error .lr-ask-bubble` | – | `background:#fca5a5; border-color:#fca5a5; color:#991b1b;` |
| Quota bar | `.lr-ask-quota-bar` | `background:var(--lr-surface); border:1px solid var(--lr-line);` | – |

---
### 7. Responsive Breakpoints
| Breakpoint | Width | Adjustments |
|------------|------|-------------|
| Mobile | ≤ 640px | - Composer sticky bottom<br>- Graph panel moves below report (`order:2`)<br>- Onboarding stepper becomes accordion (`display:block`)<br>- Font sizes stay same (use `var(--text-*)`). |
| Tablet | ≤ 959px | - Report split stays columnar but with reduced gap (`var(--space-md)`). |
| Desktop | ≥ 960px | - Full 60/40 split, sticky graph, accordion open state visible.

---
**Micro‑animations**
- All hover/focus transitions use `150ms` (fast) easing `cubic-bezier(0.2,0,0,1)`.
- Reduced‑motion respects `prefers-reduced-motion` – disables pulse and panel animations.

---
**Accessibility**
- All interactive elements have visible focus rings (`--lr-accent` teal).
- Contrast ratios meet AA on cream background.
- `aria-expanded` toggles on accordion sections.

---
*This spec is ready for the CSS patch (D3) and token delta (D4).*
