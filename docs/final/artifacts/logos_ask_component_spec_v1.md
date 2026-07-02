# Logos `/logos-research/ask` · Component Spec v1 (Pack L-Ask P0)

**Surface:** `logos.jema-ai.com/logos-research/ask` · **ASK_UI_REV:** `20260702c`  
**Scope:** `.logos-research-ask-page` only · DOM/class names **unchanged**

---

## Token map (DTCG → CSS)

| DTCG `semantic.trust.logos_ask.*` | CSS var | Hex / value |
|-----------------------------------|---------|-------------|
| bg | `--lr-ask-bg` | `#faf7f2` |
| surface | `--lr-ask-surface` | `#ffffff` |
| accent | `--lr-ask-accent` | `#2d7a68` |
| gold | `--lr-ask-gold` | `#c5a057` |
| ink | `--lr-ask-ink` | `#292524` |
| ink-soft | `--lr-ask-ink-soft` | `#57534e` |
| error | `--lr-ask-error` | `#b91c1c` |
| error-bg | `--lr-ask-error-bg` | `#fef2f2` |
| border | `--lr-ask-border` | `rgba(91,74,50,0.12)` |

Spacing/radius: reuse `--space-*`, `--radius-*`, `--text-*`.

---

## Frame C — Done (primary)

### `.logos-research-ask-page`
- **Role:** page shell, token host
- **Layout:** cream full-page bg; max-width via `.lr-ask-main`
- **States:** default only

### `.lr-ask-citation-lock`
- **Role:** first trust artifact after submit (Time-to-Trust)
- **Visual:** teal gradient strip, full width above split
- **Tokens:** border `--lr-ask-accent-border`, badge `--lr-ask-accent-soft`
- **States:** default · ref-chip hover/focus

### `.lr-ask-report-split`
- **Role:** 60/40 desktop (primary / graph); stack mobile (primary first)
- **Breakpoints:** `@media (min-width: 960px)` row · max graph 420px sticky
- **States:** default · `.lr-ask--report-expanded` widens main

### `.lr-ask-s4-section` (`data-lr-ask-s4-section="1..5"`)
- **Role:** S4 five-section cards (핵심 주장 … 다음 단계)
- **Visual:** white card, **3px left accent** teal, soft shadow
- **Tokens:** padding `--space-sm` `--space-md`, title `--lr-ask-ink`, body `--lr-ask-ink-soft`
- **States:** default · parent `.lr-ask-s4-streaming` pulse (existing)

### `.lr-ask-graph-panel` `[data-logos-ask-graph="1"]`
- **Role:** path mindmap sidecar (not LLM JSON)
- **Visual:** cream panel, viz toggle text buttons
- **Attributes:** `data-logos-ask-graph-phase`, `data-logos-ask-graph-viz` (path|full)
- **States:** skeleton · loading · done · `[data-logos-path-mindmap="1"]` SVG

### `.lr-ask-composer` · `.lr-ask-input` · `.lr-btn-primary`
- **Role:** sticky question entry (mobile bottom)
- **Primary CTA:** `--lr-ask-accent` fill; focus ring `--lr-ask-gold-ring`
- **States:** default · hover · disabled · running (`분석 중…`)

### `.lr-ask-sample-chip`
- **Role:** example questions → auto-submit
- **Visual:** scriptorium pill; teal border hover fill
- **States:** default · hover · focus-visible · disabled (while running)

---

## Frame A/B/D (summary)

| Class | Frame | Notes |
|-------|-------|-------|
| `.lr-ask-onboarding` | A Empty | 3-step; dismiss localStorage |
| `.lr-ask-quota-bar` | A | 8/8 strip; border `--lr-ask-border` |
| `.lr-ask-turn--streaming` | B | bubble pulse animation |
| `.lr-ask-turn--error` | D | `--lr-ask-error-bg` |

---

## Playwright contract (must not rename)

- `.lr-ask-citation-lock`
- `.lr-ask-s4-section` / `.lr-ask-s4-section-body`
- `.lr-ask-report-split`
- `[data-logos-ask-graph="1"]`
- `[data-logos-ask-ui-rev="20260702c"]`

---

## Forbidden on this surface

- `#5b8cff` marketing blue · hub dark · enterprise glow
- New React shell components · globals.css full replace
- Custom icon set (P0)

*SSOT: `jemaai_dtcg_tokens_proposed_v1.dtcg.json` preset `jemaai-logos-research-ask`*
