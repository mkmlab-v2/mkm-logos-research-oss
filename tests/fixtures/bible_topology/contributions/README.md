# Contributor topology shards

**Status:** `research_only` · `send_gate: HOLD`

Add PR shards under `pending/` — see repo root [CONTRIBUTING.md](../../../CONTRIBUTING.md) after export (or monorepo contributing SSOT).

**Example:** `pending/contributor_example_v1.json`

**Validate:**

```bash
py scripts/validate_bible_topology_contrib_shard_v1.py \
  --json tests/fixtures/bible_topology/contributions/pending/<shard>.json \
  --min-edges 3 --max-edges 50
```
