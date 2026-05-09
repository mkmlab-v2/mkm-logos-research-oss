# LG HS Target Board Optimization v1

작성일: 2026-05-08  
상태: Draft (research_only)  
목적: GPU 가속 개발 루프와 LG 타깃 보드 실측 확정 루프를 분리-연결해 양산 정합성을 높인다.

---

## 1. 핵심 원칙

1) GPU는 **후보 탐색/검증 가속 엔진**이다.  
2) 타깃 보드는 **최종 확정 기준**이다.  
3) 발표/대외 문구는 `로컬 기준선 -> 타깃 보드 실측 전환` 순서를 고정한다.  
4) GPU 수치만으로 양산 성능 단정 금지 (Fact-Lock).

---

## 2. GPU -> Edge 브릿지 체인 (v1)

1) **Sim2Real Sweep**
- 스크립트: `scripts/run_gpu_sim_to_edge_sweep_v1.py`
- 산출: `docs/final/artifacts/gpu_sim_to_edge_sweep_v1_latest.json`
- 목적: 정량 목표(P99 등) 기준 상위 후보 Top-K 자동 선발

2) **Safety Judge Audit**
- 스크립트: `scripts/build_athena_safety_judge_v1.py`
- 산출: `docs/final/artifacts/athena_safety_judge_v1_latest.json`
- 목적: 복합 명령 안전 판정(Go/Watch/Hold) 분포를 일관된 정책으로 점검

3) **Target-board Measurement Transition**
- D+1: 최소 기능/지연 스모크
- D+3: 위험 명령(상충/OOB) 집중 검증
- D+7: 최종 게이트(운영 진입/보완) 판정

---

## 3. 발표 시 기술 메시지 (안전 톤)

- "GPU는 개발 속도를 높이는 가속 엔진이고, 최종 성능 확정은 타깃 보드 실측으로 진행합니다."
- "저희는 후보를 GPU에서 빠르게 탐색하고, 보드 실측으로 보수적으로 확정합니다."
- "성능 과시보다 운영 안정성과 재현 가능한 검증 경로를 우선합니다."

---

## 4. 금지 표현

- "GPU에서 99% 예측되므로 보드 검증 불필요"
- "양산 성능 100% 보장"
- "경쟁사 대비 확정 우위"

---

## 5. 즉시 실행 명령

```powershell
py scripts/run_gpu_sim_to_edge_sweep_v1.py --target-p99-ms 40 --top-k 3
py scripts/build_athena_safety_judge_v1.py --sample-count 300 --seed 42
```

---

## 6. 승격 조건 (v1 제안)

- Sweep Top-3 후보 모두 `target_p99_met=true` 만족
- Safety audit에서 `HOLD`/`WATCH` 분포가 정책 허용 범위 내 유지
- 타깃 보드 실측 결과가 로컬 기준선 대비 허용 오차 내 재현

위 조건 충족 전까지는 `research_only` 상태를 유지한다.
