# DESIGN.md

## Purpose
- This document is the single source of truth for homepage UI decisions.
- It captures both visual rules and design intent so AI/tools generate consistent output.

## Scope
- Page: Homepage
- Devices: Desktop (1440), Tablet (768), Mobile (390)
- Out of scope: Admin, dashboard, internal tools

## Brand Intent
- Primary goal: Explain product value in 5 seconds.
- Tone: Trustworthy, calm, practical.
- Visual direction: Clean spacing, high readability, low visual noise.
- Product voice (recommended): "Chat-like input, report-style output."
- Domain safety intent: Guidance first, final high-risk decisions remain with professionals.

## Audience Lanes
- Consumer lane: Fast onboarding, clear benefit, low-friction start.
- Clinician/Operator lane: Safety-first framing, workflow support, evidence visibility.
- Homepage default: Show both lanes with separate CTAs.

## Design Tokens (MVP)
### Color
- `--color-bg`: #0B1020
- `--color-surface`: #121A2D
- `--color-text`: #EAF0FF
- `--color-text-muted`: #9FB0D1
- `--color-primary`: #5B8CFF
- `--color-primary-contrast`: #FFFFFF
- `--color-success`: #19C37D
- `--color-danger`: #FF5D5D

### Typography
- Font stack: Inter, Pretendard, system-ui, sans-serif
- H1: 48/56, 700
- H2: 32/40, 700
- H3: 24/32, 600
- Body: 16/24, 400
- Caption: 14/20, 400

### Spacing & Radius
- Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64
- Container max width: 1200
- Section vertical padding: 80 (desktop), 56 (mobile)
- Radius: 12 (card), 9999 (pill)

## Homepage Information Architecture
1. Hero
2. Role split (Consumer vs Clinician)
3. Social proof (logos and/or live metrics)
4. Core value/features (3-4 cards)
5. Safety/guardrail notice
6. How it works (3-4 steps)
7. CTA section
8. Footer

## Section Intent and Rules
### Hero
- Intent: Deliver one clear promise + one primary action.
- Must include: Main headline, short subcopy, primary CTA, secondary CTA.
- Limit: Headline <= 12 words, subcopy <= 24 words.
- Recommended CTA set: Start, Pricing, Demo/Ask One, My Reports.

### Role Split
- Intent: Prevent audience confusion by separating flows early.
- Must include: Consumer card + Clinician/Operator card.
- Limit: Each card has one title, one sentence, one CTA.

### Social Proof
- Intent: Reduce user hesitation quickly.
- Must include: Trusted by text or quantitative proof.
- Limit: 3-6 logos/metrics only.
- Metric rule: If metric is exploratory/baseline, label it explicitly as baseline.

### Features
- Intent: Explain why this is better, not just what it does.
- Must include: 3 cards, each with title + one sentence.
- Limit: One icon style only across cards.
- Preferred modules: Intake flow, personalization layer, guardrail engine, UX clarity.

### Safety Notice
- Intent: Build trust by clarifying responsibility boundaries.
- Must include: One plain-language disclaimer near Hero or KPI section.
- Rule: Never imply medical/legal/financial final judgment is automated.

### How It Works
- Intent: Show simple adoption path.
- Must include: Step 1-3 sequence with short labels.
- Limit: Each step description <= 16 words.

### Final CTA
- Intent: Convert ready visitors.
- Must include: One action-focused line + primary CTA button.

## Component Rules
- Buttons: Primary, Secondary only (no tertiary in MVP).
- Cards: Same elevation and padding across sections.
- Icons: Single icon family and stroke weight.
- Links: Underline on hover and visible focus ring.
- KPI cards: Keep unit formatting consistent (`%`, currency, latency).
- Badge chips: Use muted background with high-contrast text.

## Accessibility Baseline (Required)
- Text contrast must meet WCAG AA.
- All interactive elements must be keyboard reachable.
- Visible focus state required for buttons, links, and inputs.
- Images/icons that convey meaning require alt text or aria-label.

## Responsive Behavior
- Desktop: multi-column layout allowed.
- Tablet: reduce to 2 columns where applicable.
- Mobile: single column, preserve section order.
- Primary CTA must remain visible in Hero without horizontal scroll.

## Copy Guidelines
- Avoid vague claims ("best", "ultimate") without proof.
- Prefer user outcome language over feature jargon.
- Keep sentence length short and scannable.
- Keep KR/EN meaning parity if bilingual mode is enabled.
- Use "support/assist/provide insight" over "diagnose/guarantee/decide" in sensitive domains.
- For safety copy, use plain Korean first, then optional technical terms.

## Claims and Evidence Policy
- Do not present assumptions as confirmed production facts.
- Every numeric claim must map to a measurable source (artifact/report/log).
- If sample size is low, show a visible "low sample" hint.
- Separate "operational metrics" from "probe/smoke" traffic in wording when applicable.

## Definition of Done (Homepage)
- Visual consistency: tokens and spacing scale used everywhere.
- Accessibility checks: contrast, keyboard, focus passed.
- Responsive checks: 390/768/1440 reviewed.
- Performance sanity: no oversized media on first view.
- Trust checks: role split + safety disclaimer + claim labeling present.

## Change Log
- 2026-04-24: Initial minimal homepage template added.
- 2026-04-24: Customized for MKM-style homepage tone and safety framing.
