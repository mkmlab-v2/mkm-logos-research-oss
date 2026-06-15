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

## NODE_SPECS (v1 · 6 nodes)

| node_id | Anchor (start → end) | must_keep_tags | priority |
|---------|----------------------|----------------|----------|
| `prism_ops_mission_log_board` | `## 🚀 전술 작전 보드` → `### 📦 핸드오프` | `FAIL-COMP-004`, `Track A`, `SEND_GATE: HOLD` | 10 |
| `prism_ops_central_checkpoint` | `<!-- ATHENA_CHECKPOINT_V1_START/END -->` | `hygiene`, `MISSION_LOG`, `MCP lean` | 9 |
| `prism_ops_mission_log_next_one` | `**다음 1타 (레인 · 새 채팅):**` → `### 🧠 메타인지` | `Track A`, `HOLD`, `금지` | 8 |
| `prism_ops_lane_oracle` | `\| **Oracle** \|` → `\| **CROSS_REF·DSS [HYPO]** \|` | `Track A`, `실매매`, `금지` | 7 |
| `prism_ops_lane_infra` | `\| **Infra/GPU** \|` → `\| **Clinic·SDIT·Insight** \|` | `Track A`, `live`, `금지` | 7 |
| `prism_ops_lane_ms` | `\| **MS** \|` → `\| **환자·최소영 (Track B)** \|` | `MS`, `금지`, `에이전트` | 7 |

**레인 inject (병렬 채팅):** `--lane oracle|ms|infra` → board + CENTRAL + **해당 레인 1행만** (전 `다음 1타` 표 미주입).

```powershell
py scripts/build_mkm_chat_resume_pack_v1.py --lane oracle
powershell -File scripts\Invoke-MkmOpsMemoryIndexRoutine_v1.ps1 -Lane oracle
```

Library: `scripts/mkm_ops_memory_index_lib_v1.py` · `NODE_SPECS` · `LANE_OPS_PACKS`.

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

# web_ops JSON-slice overlay (gate/health → index v1.1) [HYPO]
py scripts/build_mkm_ops_memory_web_ops_overlay_v1.py
py scripts/build_mkm_chat_resume_pack_v1.py --lane web_ops
py scripts/bench_mkm_ops_memory_web_ops_retrieval_v1.py

# 풀스택 fusion (overlay 후 bench‖resume‖meta 병렬)
py scripts/run_mkm_ops_memory_web_ops_fusion_v1.py --parallel-post-overlay --include-slice

# 주간: web_ops bundle + overlay (Task MKM_WebOps_Regime_Weekly)
pwsh -File scripts/Invoke-WebOpsRegimeWeeklyRoutine_v1.ps1 -SkipLiveCdp -NoSeedBaselines -RequireDualAlignment -FailOnPointerDrift
```

**web_ops 레인 팩:** `LANE_OPS_PACKS.web_ops` = board + CENTRAL + `prism_ops_web_ops_regime_gate` + `prism_ops_web_ops_health` (JSON `json_pointer` slices).

Hygiene hook (optional weekly): `Invoke-MissionLogCentralHygiene_v1.ps1` tail rebuilds index. **`MKM_WebOps_Regime_Weekly`** runs `Invoke-WebOpsRegimeWeeklyRoutine_v1.ps1` (overlay merge after gate refresh).

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

## Ops Memory 본선 운영 확장 체크리스트 v1 (2026-06-01)

**목적:** AI-to-AI **와이어 버스 승격 없이**, Ops Memory만 **운영 SSOT 재개 규약**으로 안전 확장.  
**Track:** 운영 보조 · `[HYPO]` 유지 · **not** Track A ACTIVE · **not** live trading · **not** inter-agent wire promotion.

### 범위 고정

| IN (허용) | OUT (금지) |
|-----------|------------|
| `NODE_SPECS` 추가·anchor/tags 정합 | index JSON을 human SSOT로 승격 |
| source/inject `must_keep` 게이트 | inter-agent wire·V2 stub 본선 합선 |
| resume pack → Daily/Weekly patrol | 97.52%를 전체 컨텍스트·상용 SLA 주장 |
| 레인별 pin 분리(MS/Oracle/Infra) | Track A ACTIVE·실매매 컨텍스트 자동 주입 |
| 토큰 벤치 **3-node scope** 재측정 | must_keep = semantic QA로 과신 |

### 정밀 타격 표 (repo root · Windows)

| # | 단계 | 명령 | Pass | 실패 시 |
|---|------|------|------|---------|
| 1 | P0 경로 | `powershell -File scripts\verify_p0_constitution_gate_paths.ps1` | exit **0** | ops memory 경로 누락 — SSOT·스크립트 복구 |
| 2 | 인덱스 빌드 | `py scripts/build_mkm_ops_memory_index_v1.py` | exit **0** + `WROTE: storage/meta/mkm_ops_memory_index_v1.json` | anchor drift — `MISSION_LOG`/`CENTRAL` 앵커·태그 수정 |
| 3 | source 게이트 | `py scripts/check_mkm_ops_memory_must_keep_gate_v1.py --phase source` | exit **0** | slice에 `must_keep_tags` 없음 — SSOT 본문 또는 `NODE_SPECS` 수정 |
| 4 | resume pack | `py scripts/build_mkm_chat_resume_pack_v1.py` | exit **0** + `mkm_chat_resume_pack_latest.json` | inject 조립 실패 |
| 5 | inject 게이트 | (resume pack 빌더 내부) `phase=inject` | stdout `inject gate: OK` | pin 텍스트에 태그 누락 |
| 6 | 원클릭 루틴 | `powershell -File scripts\Invoke-MkmOpsMemoryIndexRoutine_v1.ps1` | exit **0** | 2–5 중 어디선가 실패 |
| 7 | pytest 회귀 | `py -m pytest tests/test_mkm_ops_memory_index_v1.py tests/test_bench_mkm_ops_memory_index_token_savings_v1.py -q` | **6 passed** | `mkm_ops_memory_index_lib_v1.py` 회귀 |
| 8 | 토큰 벤치 | `py scripts/bench_mkm_ops_memory_index_token_savings_v1.py` | exit **0** → `reports/mkm_ops_memory_index_token_bench_v1_latest.json` | 범위·node_count 확인 후만 % 인용 |
| 9 | 일상 patrol | `powershell -File scripts\Invoke-MkmCommandPackage_v1.ps1 -Package DailyOpsPatrol` | exit **0** · paste `OpsMem` | manifest `ops_memory_index_daily` 단계 확인 |
| 10 | Athena ops | `powershell -File scripts\Invoke-MkmCommandPackage_v1.ps1 -Package AthenaOpsMemory` | exit **0** | index+resume만 — Fact-Lock 번들 아님 |
| 11 | 주간 hygiene | `powershell -File scripts\Invoke-MissionLogCentralHygiene_v1.ps1` | exit **0** · `overall_ok=true` | index rebuild 실패 — anchor/tags |
| 12 | NODE 추가 | `NODE_SPECS` 편집 → 2–7 재실행 | source+inject **0** | 태그를 slice에 **먼저** 넣고 spec 추가 |
| 13 | slice preview | `Invoke-MkmOpsMemoryIndexRoutine_v1.ps1 -IncludeSlice` | exit **0** · inject ON 토큰 상한 확인 | 기본 ops는 **OFF**(143 tok) 유지 |
| 14 | 승격 판정 | — | **`would_change_active: false`** · human SSOT=MD | ACTIVE·live·A2A wire **HOLD** |
| 15 | Quiet 후 복구 | `Set-SchedulerQuietProfile.ps1 -Mode Quiet` 실행 후 | `Invoke-AthenaAutomationRegistryCheck` **drift 0** | **Register 5종:** `Register-TradingAutomationHealthTask.ps1 -Force` · `Register-CoreTaskConsecutiveFailureAlertTask.ps1 -Force` · `Register-SentinelTaskHealthMonitorTask.ps1 -Force` · `Register-AmsaengEosaMonitoringBundleTask.ps1` · `Register-LiveSyncHeartbeatPullTask.ps1 -SoftFail` · 백업: `reports/scheduler_quiet_mode_disable_backup_latest.json` |
| 16 | Op30 07:50 실패 | `reports/op30_scheduled_failure_triage_20260601_v1.json` | probe OK·**LastResult=1** → post-probe/rollup 의심 · **복구:** `schtasks /Run /TN MKM_Op30_MagicOrb_Envelope_Daily` | 내일 **07:50** `LastResult=0` 관측 |

### NODE 추가 절차 (레인 확장 시)

1. `MISSION_LOG` 또는 `CENTRAL`에 **must_keep_tags가 slice 안에 실제로 존재**하는 앵커 확정.
2. `scripts/mkm_ops_memory_index_lib_v1.py` → `NODE_SPECS`에 `NodeSpec` 추가 (`priority`·`essence`·`node_id` 고유).
3. 표 #2–#7 실행.
4. (선택) `build_mkm_chat_resume_pack_v1.py --top-n N` — default **3**; 레인 pin 늘리면 토큰 재벤치(#8).
5. **병렬 채팅:** MS/Oracle/Infra **별 node_id** — 한 inject에 전 레인 합치지 않음 (`mission-log-combat-ssot`).

### 본선 “GO” 한 줄 (Ops Memory만)

> `verify_p0` **0** + routine(#6) **0** + pytest(#7) **0** + resume pack pins에 `FAIL-COMP-004`·`Track A`·`HOLD`/`금지` 유지 + **Track A ACTIVE·live·A2A wire 변경 없음**.

---

## NEVER (Fact-Lock)

- Treat index JSON as human SSOT (always derived from Markdown).
- Use 97.52% as “whole context” savings without citing 5,775 vs 143 scope.
- Auto-merge B-track / 3-lens / live trading from pins or tags alone.
- Promote `[HYPO]` bench to Track A SLA or commercial headline without human sign-off.

---

## Related docs

- `.cursor/rules/mission-log-combat-ssot.mdc` · `AGENTS.md` (resume pack)
- `docs/final/CURSOR_SESSION_VALIDATION_BASELINE_V1.md` (Cursor start/mid/end vs alwaysApply)
- `docs/final/COMPRESSION_SLA_POLICY_V1.md` (Track A vs B — separate from Ops pins)
- This one-pager: dev onboarding for **Ops AI↔AI pointer layer** only.
