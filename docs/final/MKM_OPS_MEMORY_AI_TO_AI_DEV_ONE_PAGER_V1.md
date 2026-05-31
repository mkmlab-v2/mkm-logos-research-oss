# MKM Ops Memory — AI↔AI Dev One-Pager v1

**Track:** B · `[HYPO]` / `research_only` · **not** Track A · **not** live-trading gate  
**SSOT human text:** `MISSION_LOG.md` · `docs/final/CENTRAL_AGENT_MEMORY_V1.md`  
**Machine index (derived):** `storage/meta/mkm_ops_memory_index_v1.json`  
**Main on:** `gitea/main` (Ops Phase 0 + coerce + one-pager; v3 eval artifacts on disk — see below)

---

## Problem

Chat sessions do not share memory. Pasting full `MISSION_LOG.md` every turn burns tokens and mixes lanes (MS / Oracle / B-track / Track A).

## Design (3 layers)

```
Human SSOT (plain Markdown)
  MISSION_LOG anchors · CENTRAL checkpoint block
        │
        ▼  build_mkm_ops_memory_index_v1.py (deterministic anchor extract)
Machine index JSON
  node_id · file_path · anchor_start/end · line_range · essence · must_keep_tags · priority
        │
        ▼  build_mkm_chat_resume_pack_v1.py (default top_n=3, optional --include-slice)
        ▼  merge_mkm_ops_patrol_into_resume_pack_v1.py (after DailyOpsPatrol paste; field `last_ops_patrol`)
Chat inject payload
  OFF: essence + must_keep_tags only  (~143 tok, 3 nodes, tiktoken cl100k_base)
  ON:  + truncated anchor body         (~1,880 tok @ slice-max-chars 1200)
  + optional `last_ops_patrol.paste_line` (~1 line; not in must_keep inject gate)
```

**Not a new natural language.** Structured pointers + governance substring gates.

---

## NODE_SPECS (v1 · 3 nodes)

| node_id | Anchor (start → end) | must_keep_tags | priority |
|---------|----------------------|----------------|----------|
| `prism_ops_mission_log_board` | `## 🚀 전술 작전 보드` → `### 📦 핸드오프` | `FAIL-COMP-004`, `Track A`, `SEND_GATE: HOLD` | 10 |
| `prism_ops_central_checkpoint` | `<!-- ATHENA_CHECKPOINT_V1_START/END -->` | `hygiene`, `MISSION_LOG`, `MCP lean` | 9 |
| `prism_ops_mission_log_next_one` | `**다음 1타 (레인 · 새 채팅):**` → `### 🧠 메타인지` | `Track A`, `HOLD`, `금지` | 8 |

Library: `scripts/mkm_ops_memory_index_lib_v1.py` · `NODE_SPECS`.

---

## Gates (fail-fast)

| Phase | Script | Checks |
|-------|--------|--------|
| **source** | `check_mkm_ops_memory_must_keep_gate_v1.py --phase source` | Each anchor slice in SSOT files contains its `must_keep_tags` |
| **inject** | same `--phase inject --payload-text …` | Assembled resume/inject text contains **all** node tags |

Missing tag → **exit 1**. Substring match only (not semantic QA).

---

## Developer commands (repo root)

```powershell
# Build index + source gate + resume pack (no slice)
powershell -File scripts\Invoke-MkmOpsMemoryIndexRoutine_v1.ps1

# Resume pack with slice preview [HYPO]
powershell -File scripts\Invoke-MkmOpsMemoryIndexRoutine_v1.ps1 -IncludeSlice

# Token bench [HYPO] → reports/mkm_ops_memory_index_token_bench_v1_latest.json
py scripts/bench_mkm_ops_memory_index_token_savings_v1.py

# pytest
py -m pytest tests/test_mkm_ops_memory_index_v1.py tests/test_bench_mkm_ops_memory_index_token_savings_v1.py -q
```

Hygiene hook (optional weekly): `Invoke-MissionLogCentralHygiene_v1.ps1` tail rebuilds index.

---

## Measured token footprint [HYPO]

Scope: **3-node full anchor text** vs **resume inject OFF/ON** — not whole repo, not full MISSION_LOG.

| Mode | Tokens (cl100k_base) |
|------|------------------------|
| Full 3-node anchors | 5,775 |
| Inject OFF (pins) | 143 |
| Inject ON (slice 1200/ node) | 1,880 |

**Default ops:** inject **OFF** (143). Use `-IncludeSlice` only when lane “다음 1타” body needed.

Artifact: `reports/mkm_ops_memory_index_token_bench_v1_latest.json`.

---

## Orthogonal lane: Myeongni Harness v2 (do not merge with Ops inject)

| Concern | Ops memory index | Harness v2 interpret |
|---------|------------------|---------------------|
| Role | Chat resume · ops continuity | Engine pillars + LLM envelope JSON |
| GPU | No | Yes (optional `--run-llm`) |
| Coerce | N/A | `coerce_llm_envelope_to_contract_v1` (LoRA payload-echo) |
| Key scripts | `mkm_ops_memory_index_lib_v1.py` | `run_myeongri_harness_v2_engine_interpret_smoke_v1.py` · `myeongri_interpret_envelope_views_v1.py` |

LoRA training/eval: separate chat + `storage/adapters/myeongri_interpret_lora_v0/…`.

### Interpret LoRA v4 — variant curriculum (post-train · 2026-05-31)

**SSOT:** `reports/myeongri_interpret_harness_v3_v4_status_latest.json` · eval `reports/myeongri_interpret_lora_v4_eval_locked100_latest.json` · diversity `reports/myeongri_interpret_v4_diversity_audit_locked100.json`

| Metric | v3 locked100 | v4 locked100 (post-train) |
|--------|--------------|---------------------------|
| parse_ok | 1.0 | 1.0 |
| envelope_match | **1.0** | **0.0** |
| envelope_coerced | 0.0 | **1.0** |
| v3_fixed_prefix_rate | 1.0 | **0.0** |
| template_skeleton_unique | 1 | **96** (96/96 with insight) |
| narrative_diversity_gate | **fail** | **pass** |
| empty_insight rows | — | **4** (parse still ok) |

**읽는 법:** v4는 **고정 문구 암기 문제는 해소**(narrative PASS). 다만 **골드 JSON 문자열 일치(match)는 0%** — 전건 `coerce`로 governance 유지(v3와 trade-off). 주된 diff: `mkm_advanced_insight`·`confidence_score`(0.55→0.95)·`method_id`(variant vs `standard_db_*`)·`prohibition_ack` — `reports/myeongri_interpret_v4_match_mismatch_summary_latest.json`. 빈 insight **4건** → human review `fail`. **Command package (CPU):** `InterpretBtrackGate`. **Track A·실매매·Ops inject 합선 없음** · `[HYPO]` / `research_only`.

**Adapter:** `storage/adapters/myeongri_interpret_lora_v0/run_interpret_v4_variant_s100` (train 100 step · **max-seq-length 768**)

```powershell
py scripts/audit_myeongri_interpret_narrative_diversity_v1.py `
  --eval-json reports/myeongri_interpret_lora_v4_eval_locked100_latest.json `
  --predictions-jsonl reports/myeongri_interpret_lora_v4_preds_locked100_latest.jsonl `
  --out-json reports/myeongri_interpret_v4_diversity_audit_locked100.json
```

---

### Interpret LoRA v3 milestone (2026-05-31 · Fact-Lock)

**Status:** format-contract pass on holdout · **not** Track A / not Ops inject merge.

| Eval | Rows | parse_ok | envelope_match | coerced | Report |
|------|------|----------|----------------|---------|--------|
| locked25 | 25 | 1.0 | 1.0 | 0.0 | `reports/myeongri_interpret_lora_v3_eval_locked25_latest.json` |
| locked100 | 100 | 1.0 | 1.0 | 0.0 | `reports/myeongri_interpret_lora_v3_eval_locked100_latest.json` |

- **Adapter:** `storage/adapters/myeongri_interpret_lora_v0/run_interpret_v3_harness_s100` (100 train steps)
- **SFT:** `data/training/myeongri_interpret_sft_v3/{train,locked_eval}.jsonl`
- **Pipeline SSOT:** `reports/myeongri_interpret_harness_v3_pipeline_status_latest.json` (`locked100_eval.status: completed`)
- **Human review queue:** `reports/myeongri_interpret_v3_human_review_sample_latest.json` — auto triage via `apply_myeongri_interpret_v3_human_review_auto_v1.py` (`pass`/`needs_edit`/`fail`; not Track A)
- **Narrative diversity audit:** `reports/myeongri_interpret_narrative_diversity_audit_latest.json` — check `template_skeleton_unique_count` (not full-string unique alone)

```powershell
py scripts/audit_myeongri_interpret_narrative_diversity_v1.py `
  --eval-json reports/myeongri_interpret_lora_v3_eval_locked100_latest.json `
  --predictions-jsonl reports/myeongri_interpret_lora_v3_preds_locked100_latest.json
py scripts/apply_myeongri_interpret_v3_human_review_auto_v1.py
```

**Meaning of metrics:**

- `envelope_match_rate` = normalized JSON matches SFT gold envelope (curriculum/template-aligned).
- `envelope_coerced_rate: 0` = post-train path does **not** rely on `coerce_llm_envelope_to_contract_v1` template merge (contrast post_train v1 0/5).
- **Open quality gate:** human sample — 서사가 template 반복인지 (`auto_note: check_narrative_diversity`).

**Re-run eval (GPU):**

```powershell
py scripts/run_myeongri_interpret_lora_inference_eval_v1.py `
  --sft-jsonl data/training/myeongri_interpret_sft_v3/locked_eval.jsonl `
  --adapter-path storage/adapters/myeongri_interpret_lora_v0/run_interpret_v3_harness_s100 `
  --limit 100 `
  --report-json reports/myeongri_interpret_lora_v3_eval_locked100_latest.json
```

---

## Extension hooks (same pattern)

1. Add `NodeSpec` in `NODE_SPECS` (anchor + tags that **exist in slice**).
2. Rebuild index; fix SSOT if source gate fails.
3. Tune `--top-n` / `--slice-max-chars` on resume pack.
4. Re-run token bench; do **not** claim savings vs unmeasured baselines.

Prism registry pointers: `docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json` (`prism_ops_memory_index_v1`).

---

## NEVER (Fact-Lock)

- Treat index JSON as human SSOT (always derived from Markdown).
- Use 97.52% as “whole context” savings without citing 5,775 vs 143 scope.
- Auto-merge B-track / 3-lens / live trading from pins or tags alone.
- Promote `[HYPO]` bench to Track A SLA or commercial headline without human sign-off.

---

## Related docs

- `.cursor/rules/mission-log-combat-ssot.mdc` · `AGENTS.md` (resume pack)
- `docs/final/COMPRESSION_SLA_POLICY_V1.md` (Track A vs B — separate from Ops pins)
- This one-pager: dev onboarding for **Ops AI↔AI pointer layer** only.
