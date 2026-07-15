# MKM Chat Resume Pack

- generated_at_utc: `2026-07-15T10:35:48.542588Z`
- research_only: `True`
- include_slice: `False`
- repair_v2_slice: `False`
- system_status: `APPROVED_FINAL_V2`
- promotion_decision: `GO_FINAL_V2` (agent: `INTERNAL_V2_READY`)
- trackc_packet_status: `READY` (artifact READY ≠ SEND; see SEND_GATE below)
- acceptance_status: `None`

## Commander Resume (`장기기억 맥락이어`)

- trigger: `장기기억 맥락이어`
- session_end: `마무리`
- resume_mode: `standard` · `일반 재개`
- mission_log: next_one_table_pin_only — never paste full MISSION_LOG.md
- fact_lock: CONSTITUTION + scripts + exit 0 only — NL answer is not pass/fail
- SEND_GATE: `HOLD`
- send_gate_vocab: `docs/final/artifacts/mkm_send_gate_vocabulary_v1_latest.json` (narrative_lane_open ≠ SEND · promotion GO ≠ live)
- chat_tone: routine live-trading disclaimer **suppress ON** · `docs/final/artifacts/commander_chat_tone_prefs_v1_latest.json`
- chat_tone_contract: 채팅은 간결하게. 내부 격벽은 코드·아티팩트·고위험 실행 시에만 말한다. 지휘관은 실매매 안 함.
- NL 지휘부 sync: push **47/47** @ `2026-07-05T12:29:44Z` · repro: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-NotebookLmLtmGraphOpsSetup_v1.ps1 -PushNlm`

## [MISTAKE GUARDRAIL] · JEMA OS kernel ([HYPO])

- registry: `reports/mkm_agent_mistake_registry_v1.jsonl` · lane: `infra` · format: `both`

```yaml
schema: "mkm_mistake_guardrail_yaml_v1"
research_only: true
send_gate: "HOLD"
lane: "infra"
registry: "reports/mkm_agent_mistake_registry_v1.jsonl"
wall:
  - "Field(regime_map+ops gates)만 Final Action; 사상=단기 톤 보조 [HYPO][NON_GATING]; Track A·임상·실매매·단정 트리거 금지."
  - "Freeze 3-7 Done cards at multi-step start; commander outcome sentence unchanged; redefine only via new card + approval (mkm_done_card_completion_contract_v1 + mkm-done-card-completion-v1.mdc M2)."
  - "권장/추천 stop = next-1 suggestion only; cannot CLOSE OPEN commander cards (Done-card M5 + contract recommended_stop_cannot_silently_close_open_commander_cards)."
  - "User-visible DONE requires same-URL browser/snapshot OR commander ACK; scripts-only = harness DONE not product DONE (Done-card M6)."
rules:
  - id: "human_57516280f51d"
    severity: "P0"
    source: "human"
    root_cause: "done_redefinition"
    preventive: "Freeze 3-7 Done cards at multi-step start; commander outcome sentence unchanged; redefine only via new card + approval (mkm_done_card_completion_contract_v1 + mkm-done-card-completion-v1.mdc M2)."
  - id: "human_de8a35136443"
    severity: "P0"
    source: "human"
    root_cause: "권장_as_close"
    preventive: "권장/추천 stop = next-1 suggestion only; cannot CLOSE OPEN commander cards (Done-card M5 + contract recommended_stop_cannot_silently_close_open_commander_cards)."
  - id: "human_671387504111"
    severity: "P0"
    source: "human"
    root_cause: "scripts_as_ux_done"
    preventive: "User-visible DONE requires same-URL browser/snapshot OR commander ACK; scripts-only = harness DONE not product DONE (Done-card M6)."
```

- Field(regime_map+ops gates)만 Final Action; 사상=단기 톤 보조 [HYPO][NON_GATING]; Track A·임상·실매매·단정 트리거 금지.
- Freeze 3-7 Done cards at multi-step start; commander outcome sentence unchanged; redefine only via new card + approval (mkm_done_card_completion_contract_v1 + mkm-done-card-completion-v1.mdc M2).
- 권장/추천 stop = next-1 suggestion only; cannot CLOSE OPEN commander cards (Done-card M5 + contract recommended_stop_cannot_silently_close_open_commander_cards).
- User-visible DONE requires same-URL browser/snapshot OR commander ACK; scripts-only = harness DONE not product DONE (Done-card M6).

## Pin Freshness Advisory ([HYPO] · P0.3)

- stale_pins: `0` · checkpoint_contradictions: `0` · l0_l2_claim_gaps: `0` · artifact: `docs/final/artifacts/mkm_resume_pin_freshness_v1_latest.json`

## Ops Memory Pins ([HYPO])

- **prism_ops_mission_log_board** — 작전 보드 SSOT — active lanes only · Track A 금지 · SEND_GATE HOLD · must_keep: `FAIL-COMP-004`, `Track A`, `SEND_GATE: HOLD`
- **prism_ops_central_checkpoint** — CENTRAL 최신 운영 체크포인트 블록 — athena_checkpoint·격벽 스냅샷 · must_keep: `ATHENA_CHECKPOINT`, `CENTRAL`
  - slice_preview (truncated):
```
<!-- ATHENA_CHECKPOINT_V1_START -->
<!-- CENTRAL checkpoint block -->
- **2026-07-15T10:29:44Z** — Infra L4: Docker still missing; installer staged+UAC Ask Gate; tokens_per_gpu_sec null; Ollama skipped
- **2026-07-15T10:19:15Z** — Infra L4 vLLM tokens_per_gpu_sec blocked: docker_missing; Ollama baseline 132.52 tok/s kept; ask gate=Install Docker Desktop
- **2026-07-15T10:05:43Z** — 2026-07 肄붿뒪??4AI 醫낇빀蹂닿퀬??evening score ?꾨즺 [HYPO]
- **2026-07-15T09:56:10Z** — Infra GPU Top-1: Ollama gemma4:e2b live tok/s deep=132.52 skim=42.95; L4 tokens_per_gpu_sec null; SEND HOLD FAIL-COMP-004 vs TrackA 50%
- **2026-07-15T09:35:19Z** — 2026-07 肄붿뒪??4AI 醫낇빀蹂닿퀬??evening score ?꾨즺 [HYPO]
- **2026-07-15T08:15:37Z** — Logos 감시관 PASS_WITH_FINDINGS(P2 hdr)~a-codeai Paddle domain prep pack live7×200; Design cold; MS Tier3 submit remain
- **2026-07-15T07:44:02Z** — continuity=acodeai-homepage-close-2026-07-15 · a-codeai homepage+policy live DONE; next Paddle domain re-submit Tier3; SEND HOLD
- **2026-07-15T07:43:48Z** — continuity=acodeai-homepage-close-2026-07-15 · a-codeai homepage+policy LIVE DONE: deploy exit0, live 200 /,terms,privacy,refund(+ko), live_ok=true; next Paddle a
… [HYPO slice truncated]

```
- **prism_ops_mission_log_next_one** — 레인별 다음 1타 SSOT — 재개 핀 · HOLD · Track A·실매매 금지 · must_keep: `Track A`, `HOLD`, `금지`
  - slice_preview (truncated):
```
**다음 1타 (레인 · 재개용 핀):**

| 레인 | 다음 1타 |
|------|----------|
| **MS·KOSPI Field band [HYPO]** | **급등 학습체크 DONE** — `mkm_kospi_surge_learning_check_v1_latest` · learnable=`false`(관측만) · vendor 7/15≈7394(+8.6% vs 7/13 6807·잠정) · H2 YE/Aug **resolve 금지** · **다음** 종가 후 `run_kospi_daily_observation_loop_v1.py --year-month 2026-07 --as-of-kst 2026-07-15 --phase evening` · continuity `kospi-surge-learn-check-2026-07-15` · **research_only · SEND HOLD · AI주문금지** |
| **Oracle·Logos** | **Option A display diversion DONE** — live chrome `JEMA Scripture Research` · LOGOS hero wordmark 해제 · host logos.* technical only · Destiny exit0 · friend 7/7 · Cosmic ABSENT · triage `display_diversion=APPLIED` · **다음** Claude re-eval OK / counsel optional · continuity `logos-critique-faithlife-hypo-2026-07-15` · **research_only · SEND HOLD · counsel_when_commander** |
| **MS·B2B 압축** | **Paddle domain re-submit PREP DONE** — live 7 URL 200 re-verify · paste sheet `acodeai_paddle_domain_resubmit_prep_v1_latest` · checklist check exit0 · **다음** 지휘관 Tier3 `vendors.paddle.com` a-codeai-only submit (agent login 금지) · continuity `acodeai-paddle-domain-prep-2026-07-15` · **SEND HOLD · ≠pro
… [HYPO slice truncated]

```
- **prism_ops_portfolio_execution_focus** — 2026 실행 집중 — One cash cow(a-codeai)+One passion(logos) · 시장검증 ADVISORY · TRACK_C §0.6 · 체크포인트 스크롤 내성 · must_keep: `one_cash_cow_acodeai`, `ADVISORY_not_fact_lock`, `TRACK_C_IP_BUSINESS_PLAN`
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
- **prism_ops_where_used_gate** — 사용처 → Pass1 resolve+check · Pass2 cited⊆hit synthesis_ok · CENTRAL 장문 금지 · must_keep: `coverage_ok`, `resolve_mkm_where_used_v1.py`, `HOLD`, `synthesis_ok`
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
- **prism_ops_absolute_balance_conflict_state** — Absolute Balance=조율 상태 · Field→Lens(3)→Conflict→Final · 제5 AI 아님 · Final=Field+ops · must_keep: `not_fifth_ai`, `state_not_vector`, `HOLD`, `field_gates_final`
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
- **logos_oracle_tier3_anchor_3600_ceiling** — Tier-3 anchor 3600 research ceiling — HG frozen, observability+closure SSOT; resonance_cap 128 unchanged; Track A forbidden · must_keep: `logos_bible_advancement_closure_v1_latest.json`, `stage_batch_preview_exhausted`
  - paths: `docs/final/artifacts/logos_oracle_tier3_narrative_commander_signoff_v1_latest.json`, `docs/final/artifacts/logos_bible_advancement_closure_v1_latest.json`, `docs/final/artifacts/logos_oracle_narrative_closure_observability_v1_latest.json`, `scripts/Invoke-MkmOracleModuleObservabilityWeeklyRoutine_v1.ps1`

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
