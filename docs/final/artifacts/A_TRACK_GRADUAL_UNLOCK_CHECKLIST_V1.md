# A-Track 점진 해제 체크리스트 (Go/No-Go) v1

기준일 현재 B-track 품질 게이트는 전반 PASS이며, 운영 잠금은 여전히 HOLD 중심으로 유지된다.  
따라서 A-track은 "전면 해제"가 아니라 "단계별 제한 해제"만 허용한다.  
아래 표의 각 단계는 모든 필수 조건을 충족해야 다음 단계로 승격할 수 있다.

---

## 0) 현재 기준 스냅샷 (초기값)

- `high_reliability_mode_gate_latest.json`: `decision=PASS`
- `prophecy_2026_monthly_kospi_btc_fact_safe_v1.json`:
  - `high_reliability_decision=HOLD`
  - `price_output_locked=true`
  - `core_decision=HOLD`
- `trinity_track_quality_report_latest.json`: `overall_decision=PASS` (`report_only`)
- `training_result.json` (Chronos): `direction_match_rate=58.7393`, `average_error_percentage=12.3201`
- `holdout_2026_result.json` (Chronos): `direction_match_rate=41.6667`, `average_error_percentage=4.7954`
- `quad_fusion_result_20260401_125917.json`:
  - `validation_metrics.correlation=0.0666`
  - `test_metrics.correlation=0.0333`

해석: 품질/운영 게이트는 안정적이나, 실전 해제를 정당화할 예측력 지표는 아직 보수적으로 해석해야 한다.

---

## 1) 단계별 해제 표 (필수 조건 + 차단 조건)

| 단계 | 허용 범위 | Go (모두 충족) | No-Go / 즉시 HOLD |
|---|---|---|---|
| **S0 Locked (기본)** | 리포트/관측만 | 기본 상태 유지 | 해당 없음 |
| **S1 Shadow** | 실주문 없음, 의사결정 로그만 | (1) `high_reliability_mode_gate=PASS` 유지, (2) Trinity PASS 유지, (3) 최근 4주 내 중대 데이터 결손 없음 | 게이트 파일 누락/갱신 실패, 스키마 불일치 |
| **S2 Paper-Strict** | Paper trading only, 아주 낮은 사이징 | (1) `high_reliability_decision`이 연속 2회 `HOLD` 이외 상태, (2) `price_output_locked=false`, (3) Chronos holdout `direction_match_rate >= 50%` | `price_output_locked=true` 재발, holdout 방향성 급락(<45%) |
| **S3 Paper-Scaled** | Paper 규모 점진 확대 | (1) S2를 최소 4주 유지, (2) paper 손익 곡선 MDD 관리 임계 충족, (3) 월간 품질 게이트 연속 PASS | 주간 성능 급변, 롤백 플래그 발생 |
| **S4 Limited Live (승인필수)** | 제한적 실주문, 강제 킬스위치 | (1) S3 연속 8주 안정, (2) 운영자 명시 승인, (3) 롤백 자동화 사전 검증 완료 | 승인 미완료, 알림/롤백 체인 장애 |

---

## 2) 핵심 수치 임계 (초기 제안, 보수형)

아래 임계는 "전면 해제"가 아니라 S2/S3 진입용 최소선이다.

- 게이트 상태
  - `high_reliability_mode_gate_latest.decision == PASS`
  - `trinity_track_quality_report_latest.summary.overall_decision == PASS`
- 잠금 해제 관련
  - `prophecy_*_fact_safe_v1.meta.price_output_locked == false` (필수)
  - `prophecy_*_fact_safe_v1.meta.high_reliability_decision != HOLD` 2회 연속
- Chronos 품질 보강
  - holdout `direction_match_rate >= 50%` (권장 55%+)
  - holdout `average_error_percentage <= 5.0%` 유지
- Quad-Fusion 품질 보강
  - `validation_metrics.correlation`과 `test_metrics.correlation`이 롤링 기준 개선 추세
  - test 샘플 부족/비정상 값(Infinity 등) 재발 금지

---

## 3) 운영 가드레일 (해제 이후에도 고정)

- `execution_mode=paper_trading_only`를 S2/S3 동안 강제
- 초기 사이징 상한 유지: 매우 낮은 `position_scale_cap`부터 시작
- `daily_loss_cap_pct` 초과 시 당일 자동 중단
- GO 상태에서도 월간 재평가에서 `HOLD` 나오면 즉시 S0 또는 S1로 롤백
- 롤백 판단은 "단일 지표 악화"가 아니라 "게이트 실패 + 성능 악화 동시 발생" 우선

---

## 4) 최종 판단 가이드

- **현재 권고 상태**: `S1 Shadow` 유지 (관측/검증 강화)
- **즉시 할 일**:
  1. `price_output_locked` 해제 조건을 충족하는지 월간 체인에서 연속 검증
  2. Chronos holdout 방향성(50% 이상) 회복 여부 확인
  3. Quad-Fusion test 품질 지표의 연속 개선 증거 확보
- **승격 원칙**: "좋아 보이는 단발 결과"가 아니라 "연속성 + 자동 롤백 검증"이 우선

---

## 5) 승인 게이트 (필수)

S4(Limited Live) 진입은 기술 지표 충족과 별개로 운영자 명시 승인이 필요하다.  
승인 전까지는 어떤 형태의 실주문 자동화도 활성화하지 않는다.
