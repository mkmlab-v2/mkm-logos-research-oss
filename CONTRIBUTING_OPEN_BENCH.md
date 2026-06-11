# Open-bench contributions (compression + prophecy)

**Lane:** `contributor_provided` · **Track:** B-track · **SEND:** HOLD · `[HYPO]` / `research_only`

This repo accepts **community contributions** for research benches — not contracted customer data.

## What we do not claim

- No Track A 47.5% SLA headline from contributor corpora
- No `customer_provided` / SEND / live trading auto-trigger
- No auto-merge into production SSOT without commander `--human-approve-promotion`

---

## Compression (masked text / CS logs)

**Min:** 10 rows · **Kit:** `docs/final/artifacts/compression_open_bench_contributor_kit_v1_latest.json`

1. Copy format from `data/compression/examples/compression_contributor_example_v1.jsonl`
2. Each row: `contributor_provided=true`, `customer_provided=false`, `labels` includes `research_only`, masked `text` (≥40 chars)
3. Add file under `data/compression/contributions/` and an entry in `compression_contributions_manifest_v1.json`
4. Local validate:

```powershell
py scripts/validate_compression_contributor_jsonl_v1.py --jsonl data/compression/contributions/YOUR_FILE.jsonl --min-rows 10
```

5. Bench chain:

```powershell
powershell -File scripts/Invoke-CompressionContributorBenchChain_v1.ps1 -ContributorJsonl data/compression/contributions/YOUR_FILE.jsonl
```

PRs touching `data/compression/contributions/**` run CI: `.github/workflows/compression-contributor-pr-validate.yml`

---

## Prophecy (falsifiable questions + probabilities)

**Min:** 5 questions · **Kit:** `docs/final/artifacts/prophecy_open_bench_contributor_kit_v1_latest.json`

1. Copy format from `data/prophecy/examples/prophecy_contributor_example_v1.jsonl`
2. Each row: `schema=prophecy_contributor_question_v1`, clear `resolution_criteria`, binary `outcome_spec`, `forecasts[].probability_0_1`
3. Add file under `data/prophecy/contributions/` and manifest entry in `prophecy_contributions_manifest_v1.json`
4. Local validate:

```powershell
py scripts/validate_prophecy_contributor_jsonl_v1.py --jsonl data/prophecy/contributions/YOUR_FILE.jsonl --min-rows 5
```

5. Bench chain:

```powershell
powershell -File scripts/Invoke-ProphecyContributorBenchChain_v1.ps1 -ContributorJsonl data/prophecy/contributions/YOUR_FILE.jsonl
```

PRs run CI: `.github/workflows/prophecy-contributor-pr-validate.yml`

**Price hypotheses (KOSPI/BTC):** use separate B-track daily chain — not this JSONL lane (see kit `price_btrack_adjacent`).

---

## Commander promotion (maintainers only)

```text
py scripts/apply_compression_contributor_track_a_promotion_v1.py --human-approve-promotion --reviewer commander
py scripts/apply_prophecy_contributor_promotion_v1.py --human-approve-promotion --reviewer commander
```

Does **not** overwrite `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` or `general_prophecy_latest.json` automatically.

---

## Public reproduce (try without contributing)

```text
py scripts/run_compression_evidence_lv1_chain_v1.py
```

Issue templates: `.github/ISSUE_TEMPLATE/compression_contributor.yml` · `prophecy_contributor.yml`
