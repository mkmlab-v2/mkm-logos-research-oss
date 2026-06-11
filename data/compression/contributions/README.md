# Compression open-bench — contributor corpus (B-track)

**Lane:** `contributor_provided` · **Track:** B-track research only · **SEND:** HOLD

Submit **masked** chat/log JSONL here via pull request. This is **not** a customer contract lane (`customer_provided` must stay `false`).

## Quick start

1. Copy the row shape from `data/compression/examples/compression_contributor_example_v1.jsonl`.
2. Add your file under this directory, e.g. `my_domain_v1.jsonl` (**minimum 10 rows**, text ≥ 40 chars each).
3. Register it in `compression_contributions_manifest_v1.json` → `entries[]`.
4. Validate locally:

```bash
py scripts/validate_compression_contributor_jsonl_v1.py --jsonl data/compression/contributions/my_domain_v1.jsonl --min-rows 10
py scripts/check_compression_contributions_manifest_v1.py --pr-strict --validate-reference
```

5. Open a PR. CI runs `.github/workflows/compression-contributor-pr-validate.yml`.

## Required fields (each row)

| Field | Value |
|-------|--------|
| `id` | unique string |
| `text` | masked conversation or log (≥ 40 chars) |
| `contributor_provided` | `true` |
| `customer_provided` | `false` |
| `labels` | must include `contributor_provided`, `research_only` |

Optional: `domain_tag`, `send_gate: HOLD`, `ready_for_external_send: false`.

## Maintainer bench (after validate)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CompressionContributorBenchChain_v1.ps1 -ContributorJsonl data\compression\contributions\<your>.jsonl
```

Promotion to Track A active report is **manual only**:

```bash
py scripts/apply_compression_contributor_track_a_promotion_v1.py --human-approve-promotion --reviewer commander
```

## Seed corpus (reference)

| File | Rows | Note |
|------|------|------|
| `premium_cs_masked_open_bench_seed_v1.jsonl` | 20 | Masked premium CS scenarios — community seed, not customer SLA evidence |

## Forbidden

- Real PII (unmasked phone, email, RRN, card numbers)
- `customer_provided: true` on contributor rows
- Headline claims of **47.5%** Track A or enterprise SLA from contributor PoC alone
- Auto merge to production without human `--human-approve-promotion`

## SSOT

- Kit: `docs/final/artifacts/compression_open_bench_contributor_kit_v1_latest.json`
- Issue template: `.github/ISSUE_TEMPLATE/compression_contributor.yml`
- Reproduce public anchor: `py scripts/run_compression_evidence_lv1_chain_v1.py`
