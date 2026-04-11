# MKM 코어 이론 번들 v1 (FACT-only, 압축·복원·예언 축)

**역할:** `MKM12_L0_L1_L2_CLAIMS_TAGGED_FACTCHECK_2026-04-09.md` 및 동일 시기 SSOT에서 **`[FACT]`로 표기된 문장·수치·경로**만 모아, NotebookLM·브리핑용 **한 권**으로 읽기 쉽게 묶었다.  
**금지:** 본 파일이 **`CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 또는 `docs/final/artifacts/*.json`를 대체하지 않는다.** 수치·승격·게이트 판정은 항상 원본 아티팩트·스크립트가 우선이다.  
**제외:** 작전지휘 런북·성경/명리 본선 트리거·NotebookLM-only 서사는 이 번들 범위 밖이다(별도 노트·SSOT).

---

## 1. 계층·연구 게이트 (L0/L1/L2)

- **[FACT]** `L0/L1/L2` 계층 프레임은 연구 게이트 문서·아티팩트에서 확인된다.  
  - 근거: `docs/final/artifacts/dynamic_stress_causality_gate_v1.json` (`mode: research_only`)
- **[FACT]** L1/L2 관련 복원 실험 스크립트와 아티팩트가 존재한다.  
  - 근거: `scripts/run_l1_inverse_decoder_spike_test.py`, `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json`

---

## 2. 역추론(빔)·사이드 채널 (복원 측 FACT)

- **[FACT]** 역추론(빔) L1 스파이크 요약(`scoring_mode: legacy`, **`research_only: true`**)의 aggregate `avg_exact_restore_rate`는 **`0.5787037037037037`** (약 **57.87%**), 100%가 아니다. (`min`/`max`는 동일 JSON.)  
  - 근거: `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json`
- **[FACT]** 동일 노이즈 분포에 **사이드 채널** 메타데이터가 **완전히 제공될 때** 결정론 역연산으로 `exact_restore_rate = 1.0`인 연구 스파이크가 **별도로** 존재한다(LLM 빔·프로덕션 전 구간과 구분).  
  - 근거: `scripts/run_l1_permutation_channel_integrated_spike.py`, `docs/final/artifacts/l1_permutation_channel_integrated_spike_latest.json`
- **[FACT]** RS/ECC **완전 통합**은 현재 미구현/미검증으로 분리된다.  
  - 근거: `scripts/run_mkm_l1_parity_prototype.py` (`This is NOT Reed-Solomon.`), `docs/final/FACTCHECK_GEMATRIA_ENGINEERING_REPRODUCIBILITY_2026-04-09.md`
- **[FACT]** `O(N)` vs `O(N^2)` 논의는 아키텍처 주장과 실측을 분리해야 한다.  
  - 근거: `scripts/trackb_ssm_vs_tf_bench.py` (`fact_safe_note`)

---

## 3. 압축·토큰·품질 (멀티렌스 측 FACT)

- **[FACT]** 글로벌 토큰 절감률(증거 조인): `docs/final/artifacts/cost_watch_monitor_latest.json`의 `compression.global_token_saving_rate` ≈ **0.490858** (약 **49.1%**). 원천은 `compression_report`가 가리키는 `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` (`run_config.mode`: **`experimental`**, `strategy`: **`A`**, `case_count` **40**).  
- **[FACT]** 동일 리포트 `avg_reconstruction_fidelity_jaccard` ≈ **0.735** — 절감과 **의미/표면 복원 품질**은 별개이며 무손실과 혼동 금지.
- **[FACT]** 사이드 채널 스파이크(v3): 메타데이터가 완전할 때 모드별 `exact_restore_rate` **1.0**; `overhead_json_utf8_bytes_mean` 등은 노이즈 모드별로 상이(와이어 포맷을 한 줄로 고정해 말하지 말 것).  
  - 근거: `docs/final/artifacts/l1_permutation_channel_integrated_spike_latest.json`

---

## 4. 사원수·S-L-K-M (수학적으로 고정 가능한 FACT 한 줄)

- **[FACT]** MKM12 문맥에서 `S-L-K-M` 4D 벡터 프레임은 연구/분석 구조로 사용된다.
- **[FACT]** 사원수 **해밀턴 법칙** `i^2=j^2=k^2=ijk=-1` 자체는 수학적으로 타당하다.
- **[FACT]** `S-L-K-M` 벡터/사원수 관련 연구 경로와 아티팩트가 다수 존재한다.  
  - 근거 예: `docs/final/artifacts/trackb_quaternion_dynamic_v1_2_cmp.json`, `scripts/run_mkm_l1_collision_stress_test.py`

*(구체 식 `q=S+Li+Kj+Mk`, 해밀턴 곱 신경망, 비선형 `dx/dt=…` 등은 팩트체크상 대부분 **[HYPO]** — 전역 운영 단정 금지.)*

---

## 5. 코드북·우회 PoC (FACT 경계)

- **[FACT]** 이번 팩트체크의 핵심은 "코드북 폐기"가 아니라 **과장된 복원 단정 제거**다.
- **[FACT]** `O(1) 해시 룩업` 우회 PoC 파일과 재현 산출 JSON이 존재하나, 공식 문구는 **"구현 완료"가 아니라 "구현 권고/다음 실험 단계"**로 써야 한다.  
  - 근거: `scripts/l1_codebook_bypass.py`, `docs/final/artifacts/l1_codebook_bypass_poc_latest.json`
- **[FACT]** 현재 근거로 확인되는 범위: L0/L1/L2 연구 게이트 존재, RS/ECC 완전 통합 미완, 역추론 L1 스파이크 exact 복원율(100% 미만).

---

## 6. 외부 문헌 표 (MKM 통합 여부와 별개)

**§I.1**의 Nacrith·L3TC·LLMLingua 등은 **인용용 앵커**이며, **MKM12 저장소에 동일 구현이 있다는 뜻이 아니다.** 상세 표는 원본 `MKM12_L0_L1_L2_CLAIMS_TAGGED_FACTCHECK_2026-04-09.md` **§I**를 따른다.

---

## 7. 내부 SSOT 인용 (에이전트·브리핑 고정 문장)

원문 **§I.2**와 동일 선상:

- 역추론(빔) 평균 복원율 → `l1_inverse_decoder_spike_test_summary_latest.json` (`aggregate`, `generated_at_utc`, `scoring_mode`, `research_only`).
- 글로벌 토큰 절감률(join) → `cost_watch_monitor_latest.json` + `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`의 `run_config`·케이스 수.
- 사이드 채널 1.0 → `run_l1_permutation_channel_integrated_spike.py` + `l1_permutation_channel_integrated_spike_latest.json`.
- 와이어 코덱·스텁 HTTP → `scripts/l1_side_channel_wire_codec.py`, `scripts/compression_token_api_stub.py` `POST /v1/research/l1_side_channel/wire`, OpenAPI `openapi_token_compression_stub_v1.yaml` v1.1.0+.

---

## 8. 압축·복원·예언 레포 포인터 (본 번들의 “옆 동네”)

| 주제 | 경로 |
|------|------|
| 해석 파이프라인 | `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` |
| 투트랙 SLA | `docs/final/COMPRESSION_SLA_POLICY_V1.md` |
| `evaluate_report` 흐름 | `docs/final/COMPRESSION_EVALUATE_REPORT_DATA_FLOW_V1.md` |
| 연대기·H: 병행 근거 | `docs/final/COMPRESSION_RESTORATION_EVOLUTION_INDEX_V1.md` |
| 일반 예언 스키마(루트) | `docs/final/GENERAL_PROPHECY_SCHEMA_V1.json` |
| 반복 금지(벤치 혼동) | `docs/final/MKM_LESSONS_LEARNED_V1.md` (`FAIL-COMP-004`) |
| 헌법 구현 팩트 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` |
| 수학 헌법 표(확장) | `docs/final/MKM12_MATH_CONSTITUTION_FACT_LOCKED_V2.md` (원문 §H 참조) |

---

## 9. 갱신

- 팩트체크 본문이 갱신되면 **동일 [FACT] 추출을 재실행**하거나, 본 번들을 수동으로 맞춘 뒤 버전을 `V2`로 올린다.
- **후견:** `MKM_IDENTITY_AND_ROADMAP_V1.md`(별도)가 있으면 정체성·우선순위와 교차 링크한다.
