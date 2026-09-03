# MUTDA Visual Baseline v1 — Build Status

**Commander ACK:** `COMMANDER_MUTDA_VISUAL_BASELINE_V1_BUILD_ACK`

**Branch:** `feat/mutda-news-open-beta-v1`

## Written

- `projects/mutda-news-open-beta-v1/MUTDA_DESIGN_SSOT_V1.md`
- `scripts/build_mutda_news_open_beta_site_v1.py`
- `scripts/check_mutda_news_open_beta_site_v1.py`

## Intended public changes

- consumer/editorial MUTDA hub
- quiet, mobile-first design system
- News public labels: 사실 → 왜 → 다른 관점 → 그래서 무엇을 볼까
- Bible public labels: 본문 → 문맥 → 해석 → 다른 관점 → 근거
- internal governance jargon removed from ordinary rendered HTML
- Ask page becomes a consumer bridge, not an artifact/seed console
- About copy becomes consumer-facing
- Logos research workspace boundary remains KEEP

## Current evidence ceiling

`SOURCE_WRITTEN_AWAITING_LOCAL_BUILD_VALIDATION`

The GitHub branch currently does **not** expose the two sealed builder input artifacts at these referenced paths through the connector:

- `docs/final/artifacts/mkm_mutda_series_ep01_v1_latest.json`
- `docs/final/artifacts/mkm_mutda_series_format_v1_latest.json`

They were available in the original local Cursor workspace when the prior build succeeded, but their current GitHub availability is **NOT_ESTABLISHED**.

Therefore this status does **not** claim:

- Python compile PASS
- builder exit 0
- checker exit 0
- screenshot/visual PASS
- PRODUCT_DONE
- merge authorization
- deploy authorization
- LIVE promotion

## Required local validation

From the authoritative Cursor workspace after pulling this branch:

```powershell
py -m py_compile scripts/build_mutda_news_open_beta_site_v1.py scripts/check_mutda_news_open_beta_site_v1.py
py scripts/build_mutda_news_open_beta_site_v1.py
py scripts/check_mutda_news_open_beta_site_v1.py
```

Then inspect at minimum:

- 390px mobile: `/`, `/news/`, `/news/ep01/`, `/bible/`, `/ask/`, `/about/`
- desktop: same routes
- browser console errors
- broken links

If those pass, record `VISUAL_BASELINE_V1_LOCAL_VALIDATION_PASS` only. Do not merge/deploy without a separate Commander gate.
