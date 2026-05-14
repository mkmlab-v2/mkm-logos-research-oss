# 공식 대외 브리핑 v1 (최신)

## 목적
현재 Fact-Lock 아티팩트에 근거하여, 범위 경계와 거버넌스 가드레일을 명시한 대외 안전 요약을 제공합니다.

## 상태 배지
- `track`: `B_TRACK`
- `mode`: `research_only`
- `decision_role`: `non_gating`
- `promotion_gate`: `human_signoff_required`

## 기준 시점(As-Of Anchor)
- `as_of_utc`: `2026-05-07T23:42:58Z`
- `artifact_scope`: `docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json`
- `long_horizon_gate`: `docs/final/artifacts/prophecy_lens_combo_backtest_30y_latest.json` (`status=INSUFFICIENT_HISTORY_HOLD`, `available_years=4.9993`)
- `scope_note`: "본 결과는 v1 관측 구간에 한정되며, 장기 구간 일반화는 별도 검증이 필요합니다."

## 대외 5문장 핵심 본문
1. **[전략 우위]** 최신 검증 아티팩트 범위에서 `myeongni+sasang` 조합은 `best_strategy_id` 1위를 기록했으며, `cagr=4.568246`, `sharpe=5.838073`, `mdd=-0.036296`로 확인됩니다.
2. **[리스크 거버넌스]** Logos 렌즈는 단독 실행 트리거가 아닌 리스크/맥락 레이어로 운용되며, 동일 아티팩트 구간에서 단독 Logos의 `mdd=-0.151538`이 관측됩니다.
3. **[의사결정 정책]** 운영상 전역 코디네이션은 주력 레인 우선 원칙을 따르며, 사상(Sasang) veto 가드레일은 지정 조건에서 보수적 보호를 활성화할 수 있습니다.
4. **[검증 경계]** 본 문장들은 버전 고정 아티팩트와 제한된 평가 윈도우(`30y_status=INSUFFICIENT_HISTORY_HOLD`, `available_years=4.9993`)에만 근거하며, 프로덕션 승격은 정식 Promotion Loop(`B -> Commander approval -> A`)를 따릅니다.
5. **[운영 기조]** 미해결 항목이 근거 기반으로 해소될 때까지 시스템은 보수적 가드레일 운영을 유지합니다.

## 정책 해설(오해 방지)
| 정책 표면 | 현재 규칙 | 근거 |
|---|---|---|
| 글로벌 코디네이터 충돌 정책 | `primary lanes win; logos remains non-gating` | `reports/mkm_global_coordinator_v1_latest.json` |
| 사상 veto 하드 가드레일 | `most_conservative_wins=true` | `docs/final/artifacts/sasang_veto_only_active_config_latest.json` |

## 근거 블록 (1:1 매핑)
- 표준 주장 매핑: `reports/lens_claims_evidence_mapping_v1_latest.json`
- 전략 순위/MDD 근거: `docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json`
- 장기 구간(30y) 가드 근거: `docs/final/artifacts/prophecy_lens_combo_backtest_30y_latest.json`
- 사상 승격 게이트: `reports/agct_sasang_stage2_promotion_gate_v1_latest.json`
- 사상 패스트트랙 게이트: `reports/agct_sasang_stage2_fasttrack_gate_v1_latest.json`
- 사상 D+7 체크포인트: `reports/agct_sasang_stage2_d7_checkpoint_v1_latest.json`
- 트랙월/오토바인드 잠금: `docs/final/artifacts/sasang12_promotion_candidate_gate_latest.json`

## 대외 배포 필수 푸터
- 본 브리핑의 어떤 문장도 미래 성과를 보장하는 표현으로 해석되어서는 안 됩니다.
- 프로덕션 승격에는 명시적 human sign-off와 거버넌스 게이트 통과가 필수입니다.
- 기대 아티팩트가 누락된 경우 해당 주장은 `NOT_PROVEN`으로 처리합니다.
