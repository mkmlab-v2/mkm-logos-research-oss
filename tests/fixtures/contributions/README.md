# Universal Root — contributor fixture shards (monorepo)

**Status:** `[HYPO]` · `research_only` · **included in public export v1.1** (no telemetry)

Spec: `docs/research/MKM_UNIVERSAL_ROOT_CONTRIBUTOR_FIXTURE_SPEC_V1.md`

## Layout

- `pending/` — PR candidate shards (`nsm_41k_lexicon_crosswalk_contrib_<id>_v1.json`)
- `merged/` — maintainer-promoted shards (empty until human gate)

**Frozen canonical bench (do not overwrite in drive-by PR):**

- `tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json`

## Local validate (no telemetry)

```bash
py scripts/validate_universal_root_contributor_fixture_v1.py \
  --json tests/fixtures/contributions/pending/contributor_example_v1.json

py scripts/run_universal_root_contributor_bench_v1.py \
  --shard tests/fixtures/contributions/pending/contributor_example_v1.json
```

Also run OSS smoke before opening PR:

```bash
py scripts/run_universal_root_oss_cursor_smoke_v1.py
```

## Rules (summary)

- Synthetic / public-domain probes only · **no PII** · `customer_provided: false`
- 3–50 rows per shard · human maintainer merge · **no auto Track A / SEND**
