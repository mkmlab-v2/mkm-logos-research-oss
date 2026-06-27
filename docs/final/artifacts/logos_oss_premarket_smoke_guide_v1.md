# Logos Research OSS — Premarket Smoke Guide v1

**Open-core harness** for local-first Bible GraphRAG / Scriptorium structure.  
**Not** investment advice, medical advice, or doctrinal authority.

## Release gates (solo OSS)

| Gate | Status |
|------|--------|
| `oss_github_release` | **OPEN** (MIT + README + secret check) |
| `grants_customer_contracts` | **HOLD** |
| `track_a_live_trading` | **LOCKED** |

Counsel / API metering are **not** default release blockers for 1-person OSS (`mkm_solo_oss_release_policy_v1_latest.json`).

## What ships in public export

- Conflict retrieval + dynamic synthesis harness
- Gnosis **fixture sample** (`tests/fixtures/gnosis_kg_sample_v1/`)
- Ingest scripts + empty `data/logos/gnosis_kg/` layout
- Verification gates (pytest + conflict retrieval 6/6)

## What stays local (user-provided)

| Asset | Why |
|-------|-----|
| KRV / copyrighted Bible text | Copyright — user fetch + local ingest |
| Full Gnosis morphology JSON | CC-BY-SA — user `--ack-license-cc-by-sa-4` |
| KOSPI / trading regime weights | Track A wall — never in export manifest |

## 60-second clone smoke (fixture-only)

From monorepo root (`MKM_WORKSPACE_ROOT` or clone root):

```powershell
py scripts/run_logos_oss_premarket_smoke_v1.py
```

Steps inside: secret pattern scan → Gnosis fixture ingest → conflict sidecar rebuild → retrieval gate 6/6 → synthesis pytest → export manifest verify.

## Full W5 stack (monorepo maintainer)

Requires local artifacts already built:

```powershell
py scripts/run_logos_bible_full_verification_chain_v1.py --skip-live-smoke
py scripts/check_logos_bible_full_w6_prep_gate_v1.py
```

## Optional: 66-book API matrix (dev server)

```powershell
cd projects/no1kmedi
npm run dev:studio
# other terminal:
py scripts/smoke_logos_studio_66book_matrix_v1.py --base http://127.0.0.1:3020
```

## Export bundle verify / materialize

```powershell
py scripts/build_logos_oss_public_export_bundle_v1.py --verify-only
py scripts/build_logos_oss_public_export_bundle_v1.py --materialize
```

Output: `exports/mkm-logos-research-oss-v1/`

## Public GitHub push (explicit only)

```powershell
powershell -File scripts/Push-GitHub-Explicit.ps1 -Acknowledge
```

Standalone export repo includes `.github/workflows/oss-smoke.yml` (materialized from `logos_oss_github_workflow_oss_smoke_v1.yml`).

Monorepo CI: `.github/workflows/logos-oss-premarket-smoke.yml` (path-filtered).

## Lemma coverage honesty

W5 audit **100% lemma** may include `LEMMA_VERSE_CANON_STUB` placeholder edges.  
Report **stub vs Gnosis-verified** separately — do not headline stub as morphology proof.

## Reproduce SSOT

- Smoke: `py scripts/run_logos_oss_premarket_smoke_v1.py`
- Manifest: `docs/final/artifacts/logos_oss_public_export_manifest_v1.json`
- Policy: `docs/final/artifacts/mkm_solo_oss_release_policy_v1_latest.json`
