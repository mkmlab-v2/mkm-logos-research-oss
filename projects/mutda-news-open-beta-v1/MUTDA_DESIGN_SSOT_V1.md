# MUTDA Design SSOT v1

**Status:** DESIGN_BASELINE_PINNED · branch-only · no deploy authorization

## Identity

MUTDA is a **quiet question editor's room**: calm, editorial, evidence-aware, human-readable.

### Not this
- not a generic AI SaaS dashboard
- not a noisy news portal
- not a card wall
- not an internal governance console
- not a place to expose worker flags, artifact paths, NON_GATING labels, PRODUCT_DONE flags, or research-lane jargon to ordinary users

## Public information hierarchy

### Hub
Question → choose a surface.

- **뉴스 묻다** — 지금 벌어진 일을 사실부터 정리합니다.
- **성경 묻다 · Beta** — 본문과 문맥에서 질문을 시작합니다.
- Market / research surfaces remain inactive until separately authorized.

### News answer adapter
Internal kernel may keep FACT / CAUSE / LENS / DECISION, but public labels are:

1. **사실** — 무슨 일이 있었나
2. **왜** — 어떤 맥락에서 봐야 하나
3. **다른 관점** — 다르게 볼 수 있는 지점은 무엇인가
4. **그래서 무엇을 볼까** — 다음에 확인할 조건과 경로

The public surface must not expose internal routing or evidence-state syntax merely because the engine uses it.

### Bible answer adapter
Keep the approved consumer sequence:

본문 → 문맥 → 해석 → 다른 관점 → 근거 → 더 묻기

`성경 묻다 — Beta` remains Beta. `logos.jema-ai.com` remains the research/evidence workspace and is not replaced.

## Visual language

- mobile first
- warm white / paper background
- near-black editorial text
- one restrained accent color
- generous whitespace
- strong typography hierarchy
- narrow reading measure for long-form content
- minimal borders
- no decorative gradient unless it carries information
- no pill-navigation wall
- buttons should look like actions, not badges
- cards only when they improve choice or grouping

## Trust language

Public copy may say, compactly:

> Beta · 사실과 해석을 구분하고, 근거와 한계를 함께 표시합니다.

Do not expose these internal phrases as product copy:

- PRODUCT_DONE=false
- FRIEND_READY=false
- NON_GATING
- Final Action
- research assist
- secondary / footer
- internal artifact paths / repository paths

Safety and uncertainty remain enforced in content and validators; they are translated into human language rather than deleted.

## Engineering rule

`scripts/build_mutda_news_open_beta_site_v1.py` is the authoritative generator for `projects/mutda-news-open-beta-v1/public/**`.

Generated HTML must not be hand-edited as the long-term source of truth. Any visual change must survive a builder rerun.

## Validation ceiling

A visual-baseline PASS means only:

- the temporary developer-shell impression is materially reduced
- the hub → news → episode → Ask path is clearer
- internal governance jargon is removed from ordinary public presentation
- approved safety/claim ceilings remain intact

It does **not** mean:

- semantic answer quality established
- PRODUCT_DONE
- market validation
- FRIEND_READY
- deployment authorization
- LIVE promotion

## Gate

This branch may be built and checked. Merge, deploy, DNS write, LIVE promotion, advertising, and mainline redirects require separate Commander authorization.
