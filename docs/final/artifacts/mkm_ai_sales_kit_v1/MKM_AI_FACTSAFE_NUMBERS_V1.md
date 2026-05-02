# MKM AI — Fact-Safe Numbers Guard v1

**역할:** 대외·세일즈·랜딩에 넣을 **수치·퍼센트·지연**은 NotebookLM·추정이 아니라 **레포 산출 JSON·exit 0 로그**에서만 인용한다.  
**상위 SSOT:** `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §1, §7 KPI Contract, `docs/final/P0_COMMERCIALIZATION_TRACKER.md`, `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`.

## 허용 인용 원칙

1. **단일 근거 파일**을 함께 표기한다 (경로 + 갱신 시점 또는 해시).
2. **벤치·드래프트** 산출물은 `research_only` / draft 라벨을 유지하고, SLA·약속 문구와 혼동하지 않는다.
3. 금지: 무손실 100%, 지연 0, 재현률·절감률의 **측정 없는 절대값 보장**.

## P1(압축·토큰)에서 자주 쓰는 증거 슬롯 (경로만 — 수치는 실행 후 파일에서 복사)

| 지표 의도 | 산출 경로 예 (SSOT는 실행 시점 파일) |
|-----------|--------------------------------------|
| 글로벌 토큰 절감률 등 압축 KPI | `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` |
| Track A 대화 비용 시뮬 (벤치) | `docs/final/artifacts/track_a_conversational_cost_simulation_latest.json` |
| L1 RTT 부하 (드래프트) | `docs/final/artifacts/bench_l1_api_load_latest.json`, VPS 측은 `docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json` 및 런북 |
| 복원 품질 (Jaccard 등) | `scripts/report_multilens_performance_eval.py` 계열 산출 · `CONSTITUTION` Multilens eval 행 |

## 개정

- v1 / 동결 포인터: Track C SSOT `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §11 반영.
