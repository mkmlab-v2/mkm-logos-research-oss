# NotebookLM Bundle Note - command_center_followup_20260327_f

[BundleID] dss_apocrypha_command_center_followup_20260327_f_20260327_1908
[CycleTag] command_center_followup_20260327_f
[GateStatus] PASS
[AuthorityReadiness] BLOCKED
[TopAction] widen_hebrew_primary_sources

## Evidence Files

- `reports/constitution/command_center_status_latest.json`
- `reports/constitution/dss_insight_priority_latest.json`
- `reports/constitution/command_center_fusion_progress_20260327.md`
- `projects/dss-4d-ingest/outputs/frontline_latest_status.json`
- `projects/dss-4d-ingest/outputs/unified_frontline_cycle_report_command_center_followup_20260327_f.json`

## Key Findings

1. Unified frontline cycle `command_center_followup_20260327_f` finished with `overall_status=PASS`.
2. Command center remains `GO` and the recommended DSS action is `widen_hebrew_primary_sources`.
3. Insight priority loop continues in executable state (`dss_priority_cycle=OK`, single action executed).

## Candidate Rules (Pilot)

- rule_id: `fusion_overlap_token_priority_01`
  - trigger: overlap token score high and confidence high
  - expected_effect: improve full-eval pilot score
  - risk: low
  - promotion_state: PILOT (authority readiness blocked)

- rule_id: `fusion_overlap_token_priority_02`
  - trigger: medium overlap token score
  - expected_effect: AB staging signal for embedding batch
  - risk: medium
  - promotion_state: PILOT (authority readiness blocked)

## Next Command

`py scripts/run_dss_insight_priority_cycle.py --max-actions 1`

---

## 문서 라벨 규칙 (Fact-Safe)

| 라벨 | 의미 | 사용 기준 |
|------|------|-----------|
| `[FACT]` | 외부 검증 완료 사실 | Evidence Files·JSON/리포트 경로로 역추적 가능 |
| `[HYPO]` | 잠정 가설·파일럿 규칙 | Candidate Rules, 승격·권위 게이트 미통과 시 |
| `[VISION]` | 전략·로드맵 문장 | 권장 액션, 목표 상태; 현재 성능으로 단정 금지 |
| `[NON-MEDICAL]` | 비의료 고지 | 건강·체질 관련 문구 포함 시 필수 |
