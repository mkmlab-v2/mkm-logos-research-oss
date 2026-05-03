# Athena Shadow Loop Command V1 (BTC First)

Purpose: Run a daily shadow-only validation loop without violating A/B barrier.

## Command Block (copy/paste)

```text
[아테나 지시 - BTC 우선 Shadow Validation Loop]

운영 모드:
- Track B (research_only, observation_only)로만 실행.
- Track A 자동 반영/자동 룰 변경 금지.
- 모든 정책/파라미터 변경은 제안서로만 출력하고 human approval 없이는 적용 금지.

1) 우선 도메인
- 1순위: BTC
- KOSPI는 2차 확장 대상으로 분리 유지.

2) 일일 루프 (D+1 반복)
- 예측 생성: 당일 BTC 방향/리스크 시나리오를 확률 형태로 생성.
- 실측 대조: 다음 주기 실제 지표와 비교.
- 오차 분석: 실패 케이스를 렌즈별(사상/명리/성경[NON_GATING])로 분해.
- 반증 점검: 기존 가설을 뒤집는 조건 충족 여부를 기록.
- 개선 제안: 룰 변경안이 아니라 "승인 대기 제안안"만 출력.

3) 출력 형식 (강제)
- Field -> Lens -> Conflict Resolver -> Final Action -> Evidence Paths -> Unverified Items
- 모든 핵심 문장 Path/Key/Value 필수
- cite 숫자 인용 금지

4) 게이트 규칙 (강제)
- meta.high_reliability_decision=="HOLD" 또는 meta.price_output_locked==true 이면 Final Action=HOLD
- final_regime=="ATTACK"이어도 most_conservative_wins 적용
- Final Action 사유는 result.failed_reasons 원문 배열 그대로 인용

5) 성공 판정 (주간)
- 7일 누적 오차 로그 완전성(결측 0)
- 실패 케이스 분해 리포트(렌즈별) 누락 0
- 제안안과 운영 반영의 격벽 유지(무단 반영 0)

6) 고정 종료 문장
"현재 증거 범위에서는 운영 가능하나, Unverified Items 해소 전까지 HOLD 가드레일을 유지합니다."
```

## Notes
- This command is intentionally conservative and keeps live-trading safeguards intact.
- Use together with `ATHENA_UPLOAD_ONEFILE_LATEST.md` for value consistency.

