# Data Provenance — Bible Topology Fixtures (monorepo prep)

**Status:** `research_only` · `send_gate: HOLD` · internal until Repo #2 public launch

Binding spec: `docs/research/MKM_GITHUB_TWO_REPO_PORTFOLIO_V0_1.md` §6.8

## Tier A — in-repo sample (default clone target)

| File | slice_id | edges | source_type | primary_source |
|------|----------|-------|-------------|----------------|
| `tests/fixtures/bible_topology/sample/sample_topology_synoptic_passion_v1.json` | `SYNOPTIC_PASSION_WEEK_v1` | see validator report | manual · synthetic | maintainer parallel anchor groups · public verse refs |

### tier-a-synoptic-passion-v1

- **Build:** `py scripts/build_bible_topology_synoptic_passion_seed_v1.py`
- **Validate:** `py scripts/validate_bible_topology_contrib_shard_v1.py --json tests/fixtures/bible_topology/sample/sample_topology_synoptic_passion_v1.json --min-edges 3 --max-edges 500`
- **Not included:** Harrison (2007) graphics · scraped Harrison DB · full ~63k PD corpus

## Tier B — optional release assets (not in default clone)

| Asset | slice_id | edges | source_type | primary_source | sha256 |
|-------|----------|-------|-------------|----------------|--------|
| (none at launch) | — | — | — | — | — |

## Tier C — maintainer vault (not public default)

| Asset | scale | source_type | primary_source | counsel_review_date |
|-------|-------|-------------|----------------|---------------------|
| (roadmap) | ~63k | public_domain_derivative | TBD — name PD primary (e.g. TSK lineage) | pending |

## Third-party context (cite only · do not bundle)

- Christoph Römhild — KJV margin cross-reference compilation (digital edge-list tradition).
- Chris Harrison (2007) — visualization of cross-reference structure; **graphics not redistributed**.

## Forbidden claims

- We do not ship Harrison copyrighted graphics.
- Tier A seed does not prove global 63k topology integrity.
- `scripts/build_logos_63779_registry_v1.py` is **not** this cross-ref ingest path.
