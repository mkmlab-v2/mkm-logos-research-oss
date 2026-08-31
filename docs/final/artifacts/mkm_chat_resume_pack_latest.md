# MKM Chat Resume Pack

- generated_at_utc: `2026-08-31T10:19:49.742741Z`
- research_only: `True`
- include_slice: `False`
- repair_v2_slice: `False`
- system_status: `APPROVED_FINAL_V2`
- promotion_decision: `GO_FINAL_V2` (agent: `INTERNAL_V2_READY`)
- trackc_packet_status: `READY` (artifact READY ≠ SEND; see SEND_GATE below)
- acceptance_status: `None`
- S-L-K-M: S=0.2476 L=0.246 K=0.2467 M=0.2598 · source=gematria_bridge_v1:docs/final/artifacts/logos_gematria_matrix_snapshot_v1_latest.json agg=mean_n=24 · [HYPO] · NON_GATING · ≠Final Action

## Commander Resume (`장기기억 맥락이어`)

- trigger: `장기기억 맥락이어`
- session_end: `마무리`
- resume_mode: `standard` · `일반 재개`
- mission_log: next_one_table_pin_only — never paste full MISSION_LOG.md
- fact_lock: CONSTITUTION + scripts + exit 0 only — NL answer is not pass/fail
- SEND_GATE: `HOLD`
- oneshot_contract (Day1·Azure HQ underperform advice): first reply **3 lines only** — `ACTIVE_LANE=` · `ONE_SHOT_GOAL=` · `DONE_WHEN=` (disk: `py scripts/run_mkm_resume_oneshot_contract_v1.py` · `docs/final/artifacts/mkm_resume_oneshot_contract_v1_latest.md`)
- send_gate_vocab: `docs/final/artifacts/mkm_send_gate_vocabulary_v1_latest.json` (narrative_lane_open ≠ SEND · promotion GO ≠ live)
- chat_tone: routine live-trading disclaimer **suppress ON** · `docs/final/artifacts/commander_chat_tone_prefs_v1_latest.json`
- chat_tone_contract: 첫 화면=채팅 초등 보고(≤8줄). 판정 먼저. 영문 미완료 상태코드·A/B 강제 선택 금지. 미완료=아직 제품 완료 아님/눈확인 전/다음 할 일. 저위험은 기본값 진행. *elementary*.txt 기본 생성 금지. 상세=artifact JSON. paste는 명시 시에만. 서브에이전트 user-visible도 초등 완결. 지휘관 env 의식 금지.
- NL 지휘부 sync: push **0/47** @ `2026-08-01T14:23:02Z` · repro: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-NotebookLmLtmGraphOpsSetup_v1.ps1 -PushNlm`

## Pin Cue · 재개 시 먼저

1. `ACTIVE_LANE=<oracle|ms|infra|web_ops|design>`
2. `ONE_SHOT_GOAL=<one measurable goal>`
3. `DONE_WHEN=<before→after or exit0+artifact>`

- disk: `py scripts/run_mkm_resume_oneshot_contract_v1.py --lane … --goal "…" --done-when "…"`
- artifact: `docs/final/artifacts/mkm_resume_oneshot_contract_v1_latest.md`

## [MISTAKE GUARDRAIL] · JEMA OS kernel ([HYPO])

- registry: `reports/mkm_agent_mistake_registry_v1.jsonl` · lane: `infra` · format: `both`

```yaml
schema: "mkm_mistake_guardrail_yaml_v1"
research_only: true
send_gate: "HOLD"
lane: "infra"
registry: "reports/mkm_agent_mistake_registry_v1.jsonl"
wall:
  - "Field(regime_map+ops gates)만 Final Action; 3렌즈=병렬 advisory [HYPO][NON_GATING] (예측 호라이즌 매핑 폐기 · Charter); Track A·임상·실매매·단정 트리거 금지."
  - "Grant mkm_lambda_gpu_lease_v1 before Launch; 30m orphan_kill_watchdog terminates Running without valid lease; mission end Terminate+lease --clear"
  - "Run check_mkm_control_hard_gate_v1.py before answer when commander says hardgate or after relapse; simple Q = never Task/explore; stamp session forbid pin on hajima; Korean gloss only. Counter: mkm_control_hard_gate_violation_counter_v1_latest.json. @mkm-control-hard-gate-v1"
  - "Pin credit_login_email=no1kmedi; check_mkm_lambda_credit_account_gate_v1 exit0 before spin; forbid gmail launch; Terminate+Usage end required; @mkm-mistake-guardrail-lambda-wrong-account-billing-v1"
rules:
  - id: "human_c3048408d374"
    severity: "P0"
    source: "human"
    root_cause: "post_mission_terminate_missing_and_no_orphan_watchdog"
    preventive: "Grant mkm_lambda_gpu_lease_v1 before Launch; 30m orphan_kill_watchdog terminates Running without valid lease; mission end Terminate+lease --clear"
  - id: "human_ee111f9c477b"
    severity: "P0"
    source: "human"
    root_cause: "unnecessary_subagent_on_simple_clarification / open_label_theater / soft_rule_ignored"
    preventive: "Run check_mkm_control_hard_gate_v1.py before answer when commander says hardgate or after relapse; simple Q = never Task/explore; stamp session forbid pin on hajima; Korean gloss only. Counter: mkm_control_hard_gate_violation_counter_v1_latest.json. @mkm-control-hard-gate-v1"
  - id: "human_36cd8ed34f13"
    severity: "P0"
    source: "human"
    root_cause: "wrong_account_identity_non_merge_plus_terminate_theater"
    preventive: "Pin credit_login_email=no1kmedi; check_mkm_lambda_credit_account_gate_v1 exit0 before spin; forbid gmail launch; Terminate+Usage end required; @mkm-mistake-guardrail-lambda-wrong-account-billing-v1"
```

- Field(regime_map+ops gates)만 Final Action; 3렌즈=병렬 advisory [HYPO][NON_GATING] (예측 호라이즌 매핑 폐기 · Charter); Track A·임상·실매매·단정 트리거 금지.
- Grant mkm_lambda_gpu_lease_v1 before Launch; 30m orphan_kill_watchdog terminates Running without valid lease; mission end Terminate+lease --clear
- Run check_mkm_control_hard_gate_v1.py before answer when commander says hardgate or after relapse; simple Q = never Task/explore; stamp session forbid pin on hajima; Korean gloss only. Counter: mkm_control_hard_gate_violation_counter_v1_latest.json. @mkm-control-hard-gate-v1
- Pin credit_login_email=no1kmedi; check_mkm_lambda_credit_account_gate_v1 exit0 before spin; forbid gmail launch; Terminate+Usage end required; @mkm-mistake-guardrail-lambda-wrong-account-billing-v1

## Pin Freshness Advisory ([HYPO] · P0.3)

- stale_pins: `3` · checkpoint_contradictions: `6` · l0_l2_claim_gaps: `0` · artifact: `docs/final/artifacts/mkm_resume_pin_freshness_v1_latest.json`

- **contradicts_prior_checkpoint** (polarity_conflict+topic_overlap): `2026-08-31T07:58:01Z` vs `2026-08-31T04:21:27Z`
- **contradicts_prior_checkpoint** (polarity_conflict): `2026-08-31T07:58:01Z` vs `2026-08-31T03:30:16Z`
- **contradicts_prior_checkpoint** (polarity_conflict): `2026-08-31T07:58:01Z` vs `2026-08-31T02:42:10Z`

## Last Ops Patrol (paste helper)

- `[DailyOpsPatrol] 2026-08-31 WARN (Remote:pass, P0:pass, Git:pass, Resume:pass, Athena:drift:3, Env:pass, Amsaeng:pass, NL-MCP:pass, Secrets:pass; opt_fail:1) | Shadow Only | No Track A/live`

## Ops Memory Pins ([HYPO])

- **prism_ops_mission_log_board** — 작전 보드 SSOT — active lanes only · Track A 금지 · SEND_GATE HOLD · must_keep: `FAIL-COMP-004`, `Track A`, `SEND_GATE: HOLD`
- **prism_ops_central_checkpoint** — CENTRAL 최신 운영 체크포인트 블록 — athena_checkpoint·격벽 스냅샷 · must_keep: `ATHENA_CHECKPOINT`, `CENTRAL`
  - slice_preview (truncated):
```
<!-- ATHENA_CHECKPOINT_V1_START -->
<!-- CENTRAL checkpoint block -->
- **2026-08-31T10:11:23Z** — continuity=clinic-kakao-inbox · Clinic Kakao unified inbox PARK — 주 1-2건 직접 답변; harness 보존, 딜러/실연동/Playwright HOLD
- **2026-08-31T10:05:51Z** — 2026-08 肄붿뒪??4AI 醫낇빀蹂닿퀬??evening score ?꾨즺 [HYPO]
- **2026-08-31T09:50:50Z** — A_CODEAI_30_TASK_CONTROLLED_BENCHMARK_DESIGN_FREEZE_ACK: 30-task prereg frozen TASK_RUN_N=0; execution ACK separate
- **2026-08-31T09:22:30Z** — LOGOS_ASK_20_USER_G2_VALIDATION_DESIGN_FREEZE_ACK: 20-user L1-L3 prereg frozen; execution/recruitment separate ACK
- **2026-08-31T08:34:01Z** — 김지선 산후 복약·회복 안내 최종 확정: 뒷물100%외용·모유수유+영아관찰·소음·RED FLAG 차트메모
- **2026-08-31T07:58:01Z** — continuity=dpt-r-ai-rater-repair-v1-20260831 · DPT-R P0 closed: adjudication MEASUREMENT_INSTABILITY_DOMINANT, output-contract repair v2 IMPLEMENTED PASS (16/16 format, AI_RATING_N_NEW=0); WAIT disposition same36 regression 미승인; 병렬 Logos same-URL→Gov172→BESD PC-001
- **2026-08-31T07:57:48Z** — Logos Ask product ACK: same-URL dynamic UX commander ack; harness 9/9; Tier2 smoke hydration+Ps23+citations OK; softmatch_wall separate
- **2026-08-31T05:00:18Z** — Clinic Automati
… [HYPO slice truncated]

```
- **prism_ops_mission_log_next_one** — 레인별 다음 1타 SSOT — 재개 핀 · HOLD · Track A·실매매 금지 · must_keep: `Track A`, `HOLD`, `금지`
  - slice_preview (full):
```
**다음 1타 (레인 · 재개용 핀):**

| 레인 | 다음 1타 |
|------|----------|
| **MS · a-codeai [HYPO]** | Day4 REAL_UI VO drop OR Studio review · 회신대기(재발송 금지) · ≠Video1 product DONE · SEND HOLD · Track A 금지 |
| **Oracle · Logos Ask UX [HYPO]** | 병렬 P0-1 · same-URL 브라우저 눈확인 → product adjudication · harness 9/9 ≠ product DONE · SEND HOLD |
| **Oracle · Bible EP1 / SBLGNT [HYPO]** | EP1 SEMANTIC_FAIL_SEALED STOP · SBLGNT WAIT lock/lens ACK · ≠lens PASS · SEND HOLD |
| **연구 · BESD v0.2 [HYPO]** | DPT-R P0 CLOSED · WAIT disposition(same36 regression 추천·미승인) · 병렬 P0-3 PC-001↔consolidation diff · SEND HOLD |
| **연구 · Agency market [HYPO]** | PHASE1 toy 천장 HOLD 종료 · 1000일 달력 늘려 블록 만들기 금지 · historical 실행 미허가 · BESD/DPT-R과 검증 독립 · SEND HOLD |
| **Governance N80+ [HYPO]** | 병렬 P0-2 · primary blind human 172/172 → freeze · 현재 0/172 · SEND HOLD |
| **Sasang Gen2 ethics [HYPO]** | PARK · WAIT ethics+access deposit · NO unpark · Track A 금지 · SEND HOLD |
| **Infra** | 패시브 · solo band 유지 · Track A·live 금지 |
| **Design/Showroom** | 아카이브·패시브 · SEND_GATE HOLD · Track A 금지 |

**Design/Showroom (아카이브 · 패시브):** SEND_GATE: HOLD · Track A·live 금지 · 상세는 Design 레인 보드/아카이브만.

```
- **prism_ops_portfolio_execution_focus** — 2026 실행 집중 — One cash cow(a-codeai)+One passion(logos) · 시장검증 ADVISORY · TRACK_C §0.6 · 체크포인트 스크롤 내성 · must_keep: `one_cash_cow_acodeai`, `ADVISORY_not_fact_lock`, `TRACK_C_IP_BUSINESS_PLAN` · **stale_advisory** age=40.337d>max=14d
  - slice_preview (full):
```
/commercialization_phases/execution_focus_2026_07: "one_cash_cow_acodeai + one_passion_logos; hold mkmlife/personadiary/gyeokmul after phase1 min"
/commercialization_phases/phase_1: "a-codeai PoC [done] · logos pilot [done] · gyeokmul family MVP · personadiary preview"
/market_validation_advisory_2026_07/status: "ADVISORY_not_fact_lock"
/market_validation_advisory_2026_07/compression_lane: "wide_market_crowded_evidence_gap"
/market_validation_advisory_2026_07/logos_lane: "narrow_niche_institution_wtp_unproven_pmf"
/market_validation_advisory_2026_07/ssot: "TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md §0.6"
/doc_pointers/portfolio_master_index: "docs/final/MKM_PORTFOLIO_MASTER_INDEX_V1.md"
/doc_pointers/business_plan_ssot: "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md"
```
- **prism_ops_where_used_gate** — 사용처 → Pass1 resolve+check · Pass2 cited⊆hit synthesis_ok · CENTRAL 장문 금지 · must_keep: `coverage_ok`, `resolve_mkm_where_used_v1.py`, `HOLD`, `synthesis_ok` · **stale_advisory** age=31.819d>max=7d
  - slice_preview (full):
```
/ops_pin_id: "prism_ops_where_used_gate"
/essence_ko: "사용처 → Pass1 resolve+check · Pass2 cited⊆hit synthesis_ok · CENTRAL 장문 금지."
/must_keep_tags: ["coverage_ok", "resolve_mkm_where_used_v1.py", "HOLD", "synthesis_ok"]
/registry: "docs/final/artifacts/mkm_where_used_registry_v1.json"
/reproduce: ["py scripts/resolve_mkm_where_used_v1.py --topic ollama", "py scripts/check_mkm_where_used_v1.py --topic ollama --strict", "py scripts/check_mkm_where_used_synthesis_v1.py --topic ollama --text-file <draft> --strict"]
/send_gate: "HOLD"
/skill: ".cursor/skills/mkm-where-used-enum/SKILL.md"
```
- **prism_ops_absolute_balance_conflict_state** — Absolute Balance=조율 상태 · Field→Lens(3)→Conflict→Final · 제5 AI 아님 · Final=Field+ops · must_keep: `not_fifth_ai`, `state_not_vector`, `HOLD`, `field_gates_final` · **stale_advisory** age=31.819d>max=7d
  - slice_preview (full):
```
/ops_pin_id: "prism_ops_absolute_balance_conflict_state"
/essence_ko: "Absolute Balance=조율 상태 · Field→Lens(3)→Conflict→Final · 제5 AI 아님 · 렌즈는 advisory · Final=Field+ops."
/must_keep_tags: ["not_fifth_ai", "state_not_vector", "HOLD", "field_gates_final"]
/ssot_md: "docs/final/ABSOLUTE_BALANCE_CONFLICT_STATE_V1.md"
/ssot_json: "docs/final/artifacts/absolute_balance_conflict_state_v1_latest.json"
/reproduce: ["py scripts/resolve_absolute_balance_conflict_state_v1.py --strict", "py scripts/check_absolute_balance_conflict_state_v1.py --strict"]
/send_gate: "HOLD"
```

## Constitution Path Pins ([HYPO] sidecar)

- **fact_lock_p0_pointer** — Stale CONSTITUTION prose is not law — scripts/verify_p0_constitution_gate_paths.ps1 required list wins · must_keep: `verify_p0_constitution_gate_paths.ps1`
  - paths: `scripts/verify_p0_constitution_gate_paths.ps1`, `scripts/run_aramaic_mvp_chain_v1.ps1`, `scripts/run_two_track_submission_pack_v1.ps1`, `.github/workflows/dual-regime-integrity.yml`, `scripts/extract_aramaic_core_corpus_v1.py`, `tests/test_extract_aramaic_core_corpus_v1.py`, `scripts/spec_bio_sample_paper_snp_join_gate_v1.py`, `.github/workflows/bio-paper-snp-sidecar-smoke.yml`, `tests/test_bio_paper_snp_join_chain_smoke_v1.py`, `tests/test_run_bio_paper_snp_sidecar_export_and_apply_v1_cli.py`
- **logos_ops_memory_cursor_inject** — Oracle Logos Cursor inject Tier-1 module SSOT — overlay + readiness gate; ≠ CONSTITUTION full rewrite; B-track HOLD; Logos [NON_GATING] · must_keep: `run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py`, `logos_theory_implementation_wiring_v1.json`
  - paths: `scripts/build_mkm_ops_memory_logos_math_overlay_v1.py`, `scripts/run_mkm_ops_memory_logos_math_overlay_chain_v1.py`, `storage/meta/mkm_ops_memory_index_v1.json`, `docs/final/artifacts/mkm_chat_resume_pack_latest.md`, `docs/final/artifacts/logos_theory_implementation_wiring_v1.json`, `scripts/run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py`, `docs/final/artifacts/logos_oracle_cursor_inject_tier1_readiness_v1_latest.json`, `scripts/run_mkm_logos_math_ltm_a2a_chain_v1.py`, `scripts/run_
- **compression_factlock_table** — Track A/B compression SSOT paths (SLA, interpretation fact-lock, bundles) · must_keep: `COMPRESSION_SLA_POLICY_V1.md`, `COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK`
  - paths: `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`, `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md`, `docs/final/COMPRESSION_SLA_POLICY_V1.md`, `docs/final/openapi_token_compression_v2_draft.yaml`, `scripts/compression_token_api_v2_stub.py`, `tests/test_compression_token_api_v2_stub.py`, `tests/test_v2_graph_wire_selective_bridge_v1.py`, `scripts/comp_atom05_*_sweep_v1.py`, `scripts/build_mkm_inter_agent_encoding_status_v1.py`, `docs/final/artifacts

## Quick Refs
- `docs/final/CENTRAL_AGENT_MEMORY_V1.md`
- `storage/meta/mkm_ops_memory_index_v1.json`
- `storage/meta/mkm_long_term_memory_graph_v1.json`
- `docs/final/artifacts/mkm_trackc_ops_dashboard_latest.md`
- `docs/final/artifacts/mkm_trackc_ops_dashboard_exec_latest.md`
- `docs/final/artifacts/mkm_trackc_operational_acceptance_latest.json`
- `docs/final/artifacts/mkm_trackc_operations_runbook_checklist_latest.md`
- `docs/final/artifacts/MKM_CORE_PROMPT_GEMINI_ATHENA_V2.md`
- `docs/final/artifacts/MKM_GEMINI_WEB_STAFF_OFFICER_CONTRACT_V1.md`
- `docs/final/artifacts/MKM_GEMINI_WEB_STAFF_OFFICER_PASTE_V1.txt`

## Resume Commands
- `py scripts/build_mkm_ops_memory_index_v1.py`
- `py scripts/build_mkm_chat_resume_pack_v1.py --include-slice`
