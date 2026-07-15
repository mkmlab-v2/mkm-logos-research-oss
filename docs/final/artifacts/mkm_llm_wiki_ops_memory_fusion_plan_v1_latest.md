# LLM Wiki ↔ Ops Memory Fusion Plan v1

**Track:** B · `[HYPO]` · `research_only` · `SEND_GATE: HOLD`  
**Machine twin:** `docs/final/artifacts/mkm_llm_wiki_ops_memory_fusion_plan_v1_latest.json`  
**Not:** a new natural language · Track A · live trading · Notion-as-SSOT

## Verdict

Hybrid LTM = **coordinates (L0)** + **semantic export (L1)** + **truth gate (L2)**.  
Do not invent a third inject language. Wire theory via **resource pointers** only.

## Layers

| Layer | Role | SSOT / surface |
|-------|------|----------------|
| **L0** | AI↔AI coordinates (`node_id`, `must_keep`, resume pack) | `MISSION_LOG` · `CENTRAL` → ops memory index → `mkm_chat_resume_pack_latest.md` |
| **L1** | Semantic export (wiki/raw + OKF) | `LLM_WIKI_SCHEMA.md` · `memory/.../llm_wiki/` · `docs/final/artifacts/okf_bundles/` |
| **L2** | Truth / pass-fail | `CONSTITUTION_*` + runnable scripts + exit 0 + artifacts |

## Theory-relevant L0 pins (existing only)

- `prism_ops_central_checkpoint`
- `prism_ops_theory_mathematization_gate`
- `prism_ops_theory_formula_ssot`
- `prism_ops_logos_metacog_coord`
- `prism_ops_logos_cosmic_anchor_bridge`

Do **not** invent pins. Logos wiring SSOT: `logos_theory_implementation_wiring_v1.json`.

## L1 surfaces (current)

| Kind | Path |
|------|------|
| Wiki synthesis | `memory/obsidian_vault/llm_wiki/wiki/mkm_theory_mathematization_canon_v1.md` |
| OKF | `okf_bundles/han_vocology/` · `okf_bundles/ijeoma_5hang_4sang/` |
| Lint | `py scripts/check_llm_wiki_lint_v1.py` |

## Promotion path (no auto-mirror)

1. Optional Inbox / `raw/` pointer  
2. Regenerable wiki or OKF page  
3. **Structural** fact only → `athena_checkpoint.py`  
4. Lands in CENTRAL checkpoint block  
5. Rebuild ops memory index when anchors change  

Wiki / OKF / NL alone ≠ pass/fail.

**L1→L0 mirror wall:** `auto_mirror_forbidden=true` · allowlist writer `scripts/athena_checkpoint.py` · enforced in `check_llm_wiki_lint_v1.py` (`l1_to_l0_mirror_wall`).

**Unstructured inbox:** Inbox/raw → optional L1 → structural fact only → `athena_checkpoint` → L0. No invent-pin / auto-mirror.

## Legacy raw

`skipped_legacy_no_yaml` remains the **accepted default contract** (warn, not fail). Count **8** paths listed in plan JSON `legacy_raw_policy.files`. High-value pointers already YAML-normalized (`2026-06-15_…canon_pointer`, `nextgen_hybrid_ai_…`). No bulk rewrite.

## Regression

```powershell
py scripts/check_llm_wiki_lint_v1.py
py -m pytest tests/test_check_llm_wiki_lint_v1.py tests/test_export_han_vocology_okf_bundle_v1.py -q
```

Commercial readiness: `mkm_llm_wiki_commercial_readiness_v1_latest.{md,json}`.  
Fact-Lock/persona default hook: **deferred** (pytest standalone).

## Commander operating brief

See `mkm_theory_fuse_via_llm_wiki_commander_brief_v1_latest.md` (≤7 steps).
