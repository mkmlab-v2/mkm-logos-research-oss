# LLM Wiki Schema v1 (MKM · OKF-aligned)

**Status:** B-track reference · `[HYPO]` export layer · internal ops shelf (Track C knowledge interchange)  
**Updated:** 2026-07-13  
**Discoverability:** CONSTITUTION thin pointer (LLM Wiki lint 보강) · fusion plan `docs/final/artifacts/mkm_llm_wiki_ops_memory_fusion_plan_v1_latest.json` · commercial scorecard `docs/final/artifacts/mkm_llm_wiki_commercial_readiness_v1_latest.json`

Karpathy LLM-wiki pattern for agent-readable knowledge. **Does not replace** implementation SSOT (`CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`) or policy SSOT (`CENTRAL_AGENT_MEMORY_V1.md`).

## Directory layout

| Path | Role |
|------|------|
| `memory/obsidian_vault/llm_wiki/raw/` | Immutable ingest pointers · external refs · no NL auto-dump |
| `memory/obsidian_vault/llm_wiki/wiki/` | Synthesized wiki pages (regenerable) |
| `docs/final/artifacts/okf_bundles/` | **Tracked** OKF v0.1 export bundles (portable, git-shippable) |

`memory/` is gitignored locally; OKF bundles under `docs/final/artifacts/okf_bundles/` are the interchange surface for agents and external consumers.

## Dual frontmatter (MKM + OKF v0.1)

Every **YAML-frontmatter** wiki or OKF concept file carries **both** layers:

| Field | Layer | Required | Notes |
|-------|-------|----------|-------|
| `schema` | MKM | yes | `llm_wiki_wiki_v1` · `llm_wiki_raw_v1` · `okf_concept_v1` |
| `type` | OKF | yes | Interop concept type (see table below) — **not replaced** by `content_type` |
| `content_type` | MKM additive | yes (wiki YAML); recommended (OKF) | `source_summary` · `entity` · `concept` · `synthesis` |
| `title` | OKF | yes | Human title |
| `description` | OKF | recommended | One-line summary |
| `resource` | OKF | recommended | SSOT path or URL for machine follow-up |
| `tags` | OKF | recommended | YAML list |
| `timestamp` | OKF | yes | ISO-8601 UTC (`generated_at_utc` alias allowed) |
| `grade` | MKM | wiki only | `HYPO` · `FACT` · `FORBIDDEN` |
| `track` | MKM | wiki only | e.g. `B-track internal` |
| `status` | MKM soft | optional | e.g. `대기` for Inbox/promote hold — no reuse counter infra |
| `fact_lock` | MKM | wiki only | Reminder: CONSTITUTION + scripts for implementation claims |

OKF spec: [Open Knowledge Format v0.1](https://github.com/google/open-knowledge-format) (Google Cloud blog 2026-06-13). MKM adds governance fields; **do not drop** MKM fields when adding OKF.

### OKF `type` values (MKM registry)

| type | Use |
|------|-----|
| `Theory Canon` | Internal theory / mathematization synthesis |
| `Clinical Instrument` | Questionnaires, rubrics (non-diagnostic) |
| `Playbook` | Education / runbook markdown |
| `External Reference` | Web or vendor article pointer in `raw/` |
| `Metric` | Defined KPI or scoring rule |
| `Runbook` | Ops procedure (Track C / infra only) |

Producers may extend types; consumers must tolerate unknown `type` strings.

### Additive `content_type` (Karpathy/Notion-inspired · does **not** replace OKF `type`)

| content_type | Prefer when | Typical OKF `type` mapping |
|--------------|-------------|----------------------------|
| `source_summary` | Pointer / digest of one external or repo source | `External Reference` |
| `entity` | Named instrument, product, person, file-id | `Clinical Instrument` · `Metric` |
| `concept` | Stable definition / term / canon slot | `Theory Canon` (narrow) |
| `synthesis` | Multi-source assembled page | `Theory Canon` · `Playbook` · `Runbook` |

Keep **both** fields: OKF `type` = interop registry; `content_type` = wiki writing layer.

## Promotion contract

1. NL · Obsidian · OKF bundle **alone** ≠ pass/fail · ≠ Track A · ≠ live trading.
2. Durable promotion: `athena_checkpoint.py` → `CENTRAL_AGENT_MEMORY_V1.md` checkpoint block.
3. Implementation claims: `CONSTITUTION_*` + runnable `.py` / pytest / exit 0.
4. `llm_wiki/raw/`: no bulk personal diary · finance · family · PHI dumps (CENTRAL 격벽).
5. **Promote only** structural / reusable facts. One-shot chat Q&A **must not** be promoted. Soft rule: leave Inbox or set `status: 대기` — **no** hard “3× reuse” counter infrastructure.
6. Notion = optional external showroom only — **not** agent SSOT. Habit bottleneck = empty Obsidian Inbox, not missing auto-classification.

## Lint failure conditions (thin check)

Callable: `py scripts/check_llm_wiki_lint_v1.py` → `docs/final/artifacts/llm_wiki_lint_v1_latest.json`  
**Validation only** — no auto-classification.

Hard fail when a **YAML-frontmatter** page is missing:

- required dual frontmatter keys (`schema`, `type`, `title`, timestamp/`generated_at_utc`)
- `content_type` on `schema: llm_wiki_wiki_v1` (OKF: warn by default; `--strict` fails)
- `grade` / `track` when `schema: llm_wiki_wiki_v1`

Also:

- Empty vault roots → exit **0** with `skipped_empty` (not a failure).
- Legacy `raw/` pointers **without** YAML frontmatter → counted as `skipped_legacy_no_yaml` (warn), not auto-rewritten. **Accepted contract** (do not bulk-rewrite): count + paths live in fusion plan JSON `legacy_raw_policy` and lint artifact `skipped_legacy_no_yaml`.
- Reminder only (not scanned as PII classifier): `raw/` must not host bulk diary / PHI / family dumps.

## Producers (callable)

| Command | Output |
|---------|--------|
| `py scripts/synthesize_llm_wiki_theory_mathematization_v1.py` | `memory/.../wiki/mkm_theory_mathematization_canon_v1.md` |
| `py scripts/export_han_vocology_okf_bundle_v1.py` | `docs/final/artifacts/okf_bundles/han_vocology/` + `han_vocology_okf_export_v1_latest.json` |
| `py scripts/check_llm_wiki_lint_v1.py` | `docs/final/artifacts/llm_wiki_lint_v1_latest.json` |

## Regression (CI-friendly)

```powershell
py -m pytest tests/test_check_llm_wiki_lint_v1.py tests/test_export_han_vocology_okf_bundle_v1.py -q
```

Fact-Lock bundle / persona health **default include deferred** (opt-in later) — see commercial readiness scorecard.

## Reserved filenames (OKF)

- `index.md` — progressive disclosure for a directory
- `log.md` — optional chronological change log (append-only)
