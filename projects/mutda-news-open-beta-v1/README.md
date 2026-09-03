# mutda-news-open-beta-v1

OPEN_BETA static news surface for **mutda.ai**.

| Flag | Value |
|------|-------|
| OPEN_BETA | true |
| PRODUCT_DONE | **false** |
| FRIEND_READY | false |

## What this is

Minimal multi-page static HTML generated from sealed EP01:

- `docs/final/artifacts/mkm_mutda_series_ep01_v1_latest.json`
- `docs/final/artifacts/mkm_mutda_series_format_v1_latest.json`

Routes: `/`, `/news/`, `/news/ep01/`, `/bible/`, `/ask/`, `/about/` plus `robots.txt` / `sitemap.xml`.

Ask CTA deep-links to `https://jema-ai.com/ask` — Ask does **not** live on mutda.

`/bible/` = **성경 묻다 — Beta** consumer shell (local stub 5-slot UX). Does **not** replace `logos.jema-ai.com`. Not 「완성 성경 AI」. FRIEND_READY/PRODUCT_DONE remain false until evidence + commander ACK.

## Build / check

From repo root:

```powershell
py scripts/build_mutda_news_open_beta_site_v1.py
py scripts/check_mutda_news_open_beta_site_v1.py
py scripts/check_mutda_bible_ask_beta_adapter_prep_v1.py
```

## Deploy (Cloudflare Worker Assets)

Commander ACK path (sealed separately):

`docs/final/artifacts/mudda_mutda_news_open_beta_deployment_ack_v0_1_latest.json`

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-DeployMutdaNewsOpenBeta_v1.ps1
```

Dry run (no wrangler):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-DeployMutdaNewsOpenBeta_v1.ps1 -SkipDeploy
```

## Non-goals

- Not a full news portal
- No diagnosis / prescription / efficacy claims
- Does not touch a-codeai / jema-ai / mkmlife / logos deploy configs
- Harness deploy exit 0 ≠ product DONE
