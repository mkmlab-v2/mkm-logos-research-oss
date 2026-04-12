# Workspace (MKM)

**진입 SSOT:** 루트 `AGENTS.md`, `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`. 구현 여부·경로는 브리핑이 아니라 이 둘과 호출 가능 스크립트로만 판정한다.

---

## Phase A — Geometric Audit 데모 번들 (재현용)

**목적:** 예측·상용 SLA가 아니라, 로컬에서 **같은 명령 → 같은 종류의 산출/exit code**로 “디스크 기반 팩트”를 맞추기 위한 최소 세트.

| 축 | 스크립트 | 설명 |
|----|----------|------|
| 기하·블렌드 (B-track) | `scripts/spike_gematria_myeongri_blend_v0.py` | 게마트리아 4D 브리지 + 명리 4D 블렌드; **예측·교리 정확도 아님** (스크립트 docstring 참고). |
| 토큰 대비 (B-track) | `scripts/spike_sovereign_token_saving.py` | 도메인 용어 → 플레이스홀더 후 tiktoken(o200k_base) 대비; **실청구·실트래픽 아님**. |
| 헌법 경로 존재 | `scripts/verify_p0_constitution_gate_paths.ps1` | `CONSTITUTION` 등 **필수 경로 파일 존재** 스모크; `OK` + exit 0. |

### 한 번에 돌리기 (Windows, 저장소 루트)

```powershell
cd C:\workspace
py scripts/spike_gematria_myeongri_blend_v0.py --stdout-only
py scripts/spike_sovereign_token_saving.py --stdout-only --samples 20 --seed 1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_p0_constitution_gate_paths.ps1
```

**보조 (선택):** 샤드 키워드 기반 소버린 효율 스파이크는 `scripts/spike_sovereign_vocab_efficiency.py --stdout-only` — 회귀 `tests/test_sovereign_efficiency.py`.

### 면책 (한 줄)

위 스파이크는 **연구·벤치(B-track) 성격**이며, 스텁·OpenAPI만으로 **프로덕션 SaaS·무손실 보증**을 주장하지 않는다 (`docs/final/P0_COMMERCIALIZATION_TRACKER.md`, `COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`와 동일 방향).
