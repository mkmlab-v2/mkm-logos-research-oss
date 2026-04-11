# Compression: `evaluate_report` 데이터 흐름 (v1)

**역할:** `scripts/report_multilens_performance_eval.py` 내부에서 입력 텍스트가 **어떤 순서로** 라우팅·압축·채점되는지 한 장으로 고정한다.  
**성격:** 수치·GO/NO_GO·상용 적합성은 `docs/final/artifacts/*.json` 및 호출 스크립트 exit/로그가 우선. 본 문서는 **호출 구조·벤치 혼동 방지**만 다룬다.

---

## 상위 SSOT

- 해석 파이프라인 전반: `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`
- 투트랙 SLA·레일: `docs/final/COMPRESSION_SLA_POLICY_V1.md`
- 교훈(벤치 섞기 금지): `docs/final/MKM_LESSONS_LEARNED_V1.md` — **FAIL-COMP-004**

---

## 진입점

- **`evaluate_report(...)`** — 멀티렌스 벤치 리포트의 중앙 진입점.  
- **입력 JSON**은 호출부에 따라 다름 (예: `docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V1.json`, `MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json`, `general_compression_eval_input_v1.json`). **같은 함수라도 입력 스펙이 다르면 지표를 직접 비교하지 말 것.**

---

## 단계 (구현 순서 요약)

1. **도메인 라우터** — `scripts/core/domain_router.py` (`DomainSpecificRouter`), `codebook/shards/zone_*.json`에서 라우팅·정책 로드.
2. **코드북·렉시콘** — 마스터 코드북 브리지·슬롯 사전 등(호출 플래그에 따라) 용어 히트·must_keep 보강.
3. **실험 압축** — `_compress_experimental` (strategy `A|B|C`, intensity, must_keep, hangul principle).
4. **절약 상한 등** — `_apply_max_saving_cap` 등으로 캡 적용(도메인별 가변 상한은 코드 내 상수·정책 JSON과 주석 참고).
5. **(옵션) 게마트리아·4D 브리지** — `include_gematria_4d_bridge`가 켜지면 `build_gematria_metadata`, `build_gematria_4d_bridge`.  
   **`apply_gematria_4d_bridge_policy=True`** 이면 **`_bridge_aware_candidate_select`** 가 base·denser·sparser 후보를 만들고, Jaccard·가드 용어·절약·상태 거리 페널티로 **최종 후보 문자열**을 고른다.
6. **복원·품질 지표** — `_reconstruct_experimental_from_raw` 등으로 재구성 후 Jaccard·절약률·민감 무결성 등을 행 단위로 적재.

---

## CLI 래퍼와의 관계

- **`scripts/run_ultra_compression_default.py`** — `--mode universal|literal|ultra-literal`, `--apply-gematria-4d-bridge-policy`로 `evaluate_report` 인자를 고정해 **활성 리포트 JSON**을 쓴다.
- **`scripts/run_general_compression_sweep.py`** — 파라미터 그리드 스윕(일반 레일 9케이스 등). **V2 universal 단일 리포트와 숫자를 한 그릇으로 쓰지 말 것.**

---

## 외부 프레임: ACON(문헌) vs 본 레포 (개념 매핑 v0)

문헌에서 **ACON**은 보통 *Augmented Context Optimization* — 장기 에이전트 맥락을 압축할 때 **실패 쌍(풀 맥락 성공 vs 압축 맥락 실패)**을 분석해 **자연어 압축 가이드라인**을 갱신하는 쪽에 가깝다. 공개 출처 예: [arXiv:2510.00615](https://arxiv.org/abs/2510.00615), 구현 참고 [microsoft/acon](https://github.com/microsoft/acon).

본 레포에는 **ACON이라는 패키지명·동일 파이프라인**은 없다. 아래는 **“비슷한 역할을 누가 담당하는지”**만 대응시킨 것이며, **수치·성능 동등 주장 금지**.

| ACON 쪽 개념 (요지) | 본 레포에서 가장 가까운 것 | 갭 / 주의 |
|---------------------|---------------------------|-----------|
| 실패 기반 가이드라인 개선 | `report_compression_jaccard_loss_patterns*.py` 산출, `generate_shard_patch_proposal_v1.py` 제안, 도메인 가드·스윕 NO_GO | ACON은 **NL 가이드** 갱신; 우리는 **코드북/샤드·게이트 JSON·스윕** 중심 |
| 맥락 압축으로 토큰 예산 절감 | `_compress_experimental` + 캡, 절약률·Jaccard 측정 | 벤치·입력 JSON이 다르면 지표 혼동 (FAIL-COMP-004) |
| “판단력” 유지 가중 | `_bridge_aware_candidate_select`의 fidelity·guard·saving·distance 가중, `must_keep` / `_bridge_policy_terms_for_state16` | **가중치는 코드 상수**; ACON 논문과 **동일 최적화 문제 아님** |
| 장기 에이전트 런타임 | 본 문서 범위 **밖** — 운영 에이전트 루프는 `AGENTS.md`·OPS 체인 참고 | ACON 벤치(AppWorld 등)와 **직접 비교 실험 미실시** 시 주장 불가 |

**후속(선택):** ACON 스타일 **실패 쌍 수집**을 `compression_jaccard_loss_patterns` 케이스와 **명시적으로 연결**할지는 별도 설계·데이터 계약이 필요하다. 본 절은 **이름 혼동 방지**용 v0이다.
