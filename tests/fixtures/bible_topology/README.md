# Bible topology fixtures (Repo #2 prep · monorepo)

**Status:** `research_only` · `send_gate: HOLD`

Tier A seed shards for `mkm-bible-topology-crosswalk` (not yet public). See `DATA_PROVENANCE.md`.

**Reproduce:**

```bash
py scripts/build_bible_topology_synoptic_passion_seed_v1.py
py scripts/validate_bible_topology_contrib_shard_v1.py \
  --json tests/fixtures/bible_topology/sample/sample_topology_synoptic_passion_v1.json \
  --min-edges 3 --max-edges 500
```

**Parent engine:** https://github.com/mkmlab-v2/mkm-universal-root
