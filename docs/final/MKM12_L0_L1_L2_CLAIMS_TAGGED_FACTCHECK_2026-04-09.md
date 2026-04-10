# MKM12 L0/L1/L2 설명문 태그 교정본 (2026-04-09)

## 3문장 요약
이 문서는 기존 설명문을 보존하면서 문장 단위로 `[FACT]`, `[HYPO]`, `[VISION]` 태그를 부여한 교정본이다.  
핵심 원칙은 "저장소 경로와 아티팩트로 재현 가능한 내용만 FACT"이며, 수학식/서사는 구현 근거가 없으면 HYPO로 분리한다.  
특히 `100% 무손실 복원`, `RS/ECC 완전 적용`, `Nacrith/CDF-24 고정 수치`는 현재 운영 팩트로 단정하지 않는다.

---

## A) 비유 기반 L0 -> L1 -> L2 설명 교정

- [FACT] `L0/L1/L2` 계층 프레임 자체는 연구 게이트 문서에서 확인된다.
  - 근거: `docs/final/artifacts/dynamic_stress_causality_gate_v1.json` (`mode: research_only`)
- [HYPO] "절대 틀리면 안 되는 리터럴을 금고로 우회한다"는 서사는 방향성 설명으로 유효하나, 전 구간에서 완전 보장으로 단정하면 과장이다.
- [HYPO] `Nacrith`, `CDF-24`, `0.93 bpb`, `원본 11%`, `Gzip 대비 3배` 수치는 현재 SSOT 경로에서 직접 검증되지 않았다.
- [FACT] L1/L2 관련 복원 실험 스크립트와 아티팩트는 존재한다.
  - 근거: `scripts/run_l1_inverse_decoder_spike_test.py`, `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json`
- [FACT] 역추론(빔) L1 스파이크 요약(`generated_at_utc: 2026-04-10T00:01:38+00:00`, `scoring_mode: legacy`)의 aggregate `avg_exact_restore_rate`는 약 **`0.5787`** (약 **57.9%**)이며 100%가 아니다. (`min` 약 0.5389, `max` 약 0.6167.)
  - 근거: `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json` — 수치·스코어링 모드는 해당 파일 재실행 시 변할 수 있음.
- [FACT] 동일 노이즈 분포에 **사이드 채널**(swap/typo/oov 메타데이터)이 **완전히 제공될 때** 결정론 역연산으로 `exact_restore_rate = 1.0`인 연구 스파이크가 별도로 존재한다(LLM 빔 복원·프로덕션 전 구간과 구분).
  - 근거: `scripts/run_l1_permutation_channel_integrated_spike.py`, `docs/final/artifacts/l1_permutation_channel_integrated_spike_latest.json`
- [HYPO] "동기화된 AI 모델 상태만 같으면 글자 하나도 안 틀리고 100% 복원"은 연구 목표 서사로는 가능하나 현재 운영 팩트가 아니다.
- [VISION] "지어내지 않고 정확도를 높이는 단계적 복원 체계"라는 목표 진술은 유지 가능하다.

---

## B) 4개 카테고리(수식/법칙) 교정

### 1) 4D 사원수 및 S-L-K-M 매핑
- [FACT] `S-L-K-M` 벡터/사원수 관련 연구 경로와 아티팩트는 다수 존재한다.
  - 근거: `docs/final/artifacts/trackb_quaternion_dynamic_v1_2_cmp.json`, `scripts/run_mkm_l1_collision_stress_test.py`
- [HYPO] 해밀턴 규칙(`i^2=j^2=k^2=ijk=-1`) 자체는 수학적으로 맞지만, 해당 식이 현재 MKM12 운영 경로에서 직접 실행/검증되는 핵심 증거로 단정하기는 어렵다.
- [HYPO] `q = S + Li + Kj + Mk`를 시스템 전체의 확정 구현식으로 단정하는 표현은 과장 소지가 있다.

### 2) 비선형 동역학 예측 방정식
- [HYPO] `dx/dt = F_사상 + G_환경 + H_개입 + xi(t)` 서술은 일부 큐레이션 텍스트에 존재하나, 운영 SSOT 코드 경로에서 고정된 단일 지배 방정식으로 확정하기는 어렵다.
  - 참고 근거: `reports/notebooklm_top10_curated_*` 계열은 설명 자료이며 구현 SSOT로 단정 불가.
- [HYPO] `gamma=0.15` 등 체질별 계수를 현재 운영 엔진의 확정 상수로 단정하는 것은 근거 부족이다.

### 3) ICD 통합 모델/병리 수준 공식
- [HYPO] `DCV = f(PD, SD)` 및 `P-Level (SL/IL/DL)` 규칙은 큐레이션/설명 텍스트에서 확인되지만, 프로덕션 검증 체계로 고정된 수식임을 단정하기 어렵다.
- [VISION] 내부 분석 프레임으로 활용하는 것은 가능하나, 외부 공식 메시지에서는 "연구/설명 레이어"임을 명시해야 안전하다.

### 4) ECC/RS 및 실시간 디코딩
- [FACT] RS/ECC 완전 통합은 현재 미구현/미검증 상태로 분리되어 있다.
  - 근거: `scripts/run_mkm_l1_parity_prototype.py` (`This is NOT Reed-Solomon.`)
  - 근거: `docs/final/FACTCHECK_GEMATRIA_ENGINEERING_REPRODUCIBILITY_2026-04-09.md`
- [HYPO] `Lambda(x)S(x)=...` 식 기반으로 "손상 문자 100% 복원"을 현재 시스템의 운영 팩트로 단정할 수 없다.
- [HYPO] RWKV 식(`w_t`, `wkv_t`)을 현 시스템의 주 복원 경로로 확정하는 근거는 부족하다.
- [FACT] `O(N)` vs `O(N^2)`는 아키텍처 레벨 주장과 실측 결과를 분리해야 한다.
  - 근거: `scripts/trackb_ssm_vs_tf_bench.py` (`fact_safe_note`)

---

## C) 외부 공유용 안전 문안 (치환본)

MKM12는 현재 하이브리드 리스크 제어 + 구조 보존 기반의 복원 연구 체계를 운영하고 있다. `[FACT]`  
4D/사원수와 L0/L1/L2 개념은 재현 가능한 연구 경로에서 유의미한 신호를 보이지만, RS/ECC 기반 100% 무손실 복원은 아직 연구 단계다. `[FACT]`  
따라서 수학식과 고압축 서사는 `[HYPO]`로 표시하고, 외부 커뮤니케이션은 재현 산출물과 승격 게이트를 중심으로 제한한다. `[FACT]`

---

## D) 앵커 경로 (SSOT 우선)

- `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`
- `docs/final/FACTCHECK_GEMATRIA_ENGINEERING_REPRODUCIBILITY_2026-04-09.md`
- `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json`
- `docs/final/artifacts/l1_permutation_channel_integrated_spike_latest.json`
- `docs/final/artifacts/dynamic_stress_causality_gate_v1.json`
- `docs/final/artifacts/trackb_quaternion_dynamic_v1_2_cmp.json`
- `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` §9 (B-track → Track A / production promotion readiness 체크리스트 v1)
- `scripts/run_mkm_l1_parity_prototype.py`
- `scripts/trackb_ssm_vs_tf_bench.py`

**SSOT 드리프트 가드:** 역추론 스파이크 복원율 문구는 항상 `l1_inverse_decoder_spike_test_summary_latest.json`의 `aggregate`·`generated_at_utc`·`scoring_mode`·`research_only`를 따른다. 불일치 시 본 문서 A)·E)·`FACTCHECK_GEMATRIA_ENGINEERING_REPRODUCIBILITY_2026-04-09.md` 스파이크 절을 아티팩트 우선으로 수정한다. **승격(연구→상용) 판단**은 위 플레이북 §9 체크리스트·지휘관 승인으로만 고정한다(NotebookLM 브리핑 단독 근거 금지).

---

## E) 코드북 해석 논쟁 교정본 (추가, 2026-04-09)

### 1) 핵심 메시지
- [FACT] 이번 팩트체크의 핵심은 "코드북 폐기"가 아니라 "과장된 복원 단정 제거"다.
- [FACT] 폐기된 것은 코드북 자체가 아니라, 현재 근거 없이 "LLM 제약만으로 100% 복원 가능"이라고 단정하는 표현이다.
- [VISION] 코드북은 연구/운영 경계 안에서 역할을 재정의해 유지할 수 있다.

### 2) 현황 진단
- [FACT] `L0/L1/L2` 계층 프레임은 연구 게이트 문서에 존재한다.
  - 근거: `docs/final/artifacts/dynamic_stress_causality_gate_v1.json`
- [FACT] RS/ECC 완전 통합은 아직 미검증 상태다.
  - 근거: `scripts/run_mkm_l1_parity_prototype.py` (`This is NOT Reed-Solomon.`)
- [FACT] 역추론(빔) L1 스파이크 요약의 aggregate 평균 exact restore rate는 최신 아티팩트 기준 약 **`0.5787`** (약 **57.9%**, `scoring_mode: legacy`)다.
  - 근거: `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json`
- [HYPO] "코드북 전면 폐기 시 즉시 위 베이스라인(aggregate 참조)으로 회귀"는 방향성 설명으로는 가능하나 인과 단정 문구로는 과장 소지가 있다.

### 3) 수치/자산 주장 판정
- [HYPO] `1.5GB 오라클 코드북` 용량 단정은 현재 워크스페이스에서 직접 근거를 확인하지 못했다.
- [HYPO] `7030배 지연`, `605배 메모리 폭증` 수치는 현재 레포 경로에서 원출처를 확인하지 못했다.
- [FACT] 미확인 수치는 외부/내부 공식 브리프에서 FACT로 표기하지 않는다.

### 4) 전략 권고 (팩트 안전 버전)
- [VISION] 코드북을 "LLM 추론 대상"이 아니라 "결정론적 보조 룩업 자산"으로 위치시키는 방향은 합리적이다.
- [FACT] `O(1) 해시 룩업` 우회 PoC 파일이 추가되었고 재현 산출 JSON이 생성되었다.
  - 근거: `scripts/l1_codebook_bypass.py`
  - 근거: `docs/final/artifacts/l1_codebook_bypass_poc_latest.json`
- [FACT] 따라서 현재 공식 문구는 "구현 완료"가 아니라 "구현 권고/다음 실험 단계"로 표기해야 한다.

### 5) 즉시 사용 가능한 안전 문안
MKM12는 코드북을 폐기한 것이 아니라, 연구/운영 경계를 지키는 방식으로 사용 위치를 재설계하는 단계에 있다. [FACT]  
현재 근거로 확인되는 범위는 L0/L1/L2 연구 게이트 존재, RS/ECC 완전 통합 미완, 그리고 역추론 L1 스파이크 요약 JSON에 기재된 exact 복원율(100% 미만)이다. [FACT]  
따라서 코드북 기반 우회 룩업 전략은 유효한 설계 후보이되, 구현/벤치가 확보되기 전까지는 [HYPO]로 분리해 운용한다. [FACT]

---

## F) 합동 회의 결과 — 재수립 작업일정 (v1, 3일 스프린트)

### Day 0 (오늘, 즉시 반영)
- [FACT] 소스 위생 정책 적용: legacy/obsolete 경로 기본 제외.
  - 적용: `scripts/build_formula_precision_core20.py` (`--allow-legacy-obsolete` 미사용 시 기본 차단)
- [FACT] 일일 브리프 경계 강화: `[FACT]/[HYPO]/[VISION]` 및 historical-reference 규칙 자동 삽입.
  - 적용: `scripts/run_notebook_compression_full_chain.ps1`
- [FACT] 산출물 추가: `docs/final/artifacts/notebook_source_hygiene_latest.json`

### Day 1 (체인 검증)
- [FACT] 수동 1회 실행 후 생성물 점검:
  - `docs/final/artifacts/notebook_compression_daily_brief_latest.md`
  - `docs/final/artifacts/notebook_source_hygiene_latest.json`
  - `docs/final/artifacts/notebook_compression_full_chain_status_latest.json`
- [FACT] NotebookLM 반영 시 브리프 상단에 historical-reference 문구 노출 여부 확인.
- [HYPO] 과거/폐기 소스가 여전히 상위 컨텍스트를 점유하면 core20 선별 가중치 추가 조정(패널티 상향) 검토.

### Day 2 (코드북 우회 PoC 착수)
- [VISION] `l1_codebook_bypass.py` PoC 초안 구현:
  - 입력: literal token set
  - 처리: dict/hash 기반 룩업
  - 출력: 복원 삽입 payload
- [FACT] 목표는 "구현 존재 + 재현 가능한 벤치 JSON" 확보이며, 성능 단정은 금지.
- [FACT] 완료 상태: PoC 구현 및 1회 실행 완료.
  - 산출: `docs/final/artifacts/l1_codebook_bypass_poc_latest.json`

### Day 3 (게이트/승격 판단)
- [FACT] Go/No-Go 조건:
  - 브리프에 경계 문구 자동 삽입 100%
  - legacy/obsolete 기본 제외 유지
  - PoC 스크립트 + 최소 1개 벤치 아티팩트 존재
- [HYPO] 성능 우수 시에도 즉시 운영 승격 금지, B-track 유지 후 추가 검증.

---

## G) 수식 묶음 클린 버전 (문장별 태그)

### 1) 4D 사원수(Quaternion) 및 S-L-K-M 매핑
- [FACT] MKM12 문맥에서 `S-L-K-M` 4D 벡터 프레임은 연구/분석 구조로 사용된다.
- [HYPO] "기본 데이터 구조가 전면적으로 사원수 대수학 기반"이라는 단정은 현재 운영 팩트로 확정하기 어렵다.
- [FACT] 해밀턴 법칙 `i^2=j^2=k^2=ijk=-1` 자체는 수학적으로 타당하다.
- [HYPO] `ij=k, ji=-k` 비가환성이 현재 운영 복원 파이프라인에서 "영구 결합 보장"으로 구현 완료됐다는 단정은 과장 소지가 있다.
- [HYPO] `q=S+Li+Kj+Mk`는 설명용 모델식으로는 유효하나, 시스템 전역의 확정 구현식으로 단정하기는 어렵다.
- [HYPO] 해밀턴 곱 기반 QNN 식(`W⊗x=...`)이 현재 운영 경로의 핵심 엔진으로 배선되었다는 근거는 부족하다.

### 2) 비선형 동역학 예측 방정식
- [HYPO] `dx/dt = F_사상(x,theta)+G_환경(x,e)+H_개입(x,u)+xi(t)`는 설명/연구 서사로는 가능하나, 운영 SSOT의 단일 지배 방정식으로 확정하기 어렵다.
- [HYPO] 체질별 계수(예: `gamma=0.15`)를 현행 운영 상수로 단정하는 것은 근거 부족이다.
- [VISION] 상태전이 예측을 비선형 동역학 형태로 정식화하려는 방향성은 연구 로드맵으로 유지 가능하다.

### 3) ICD 통합 모델 및 병리 수준 공식
- [HYPO] `DCV=f(PD,SD)`와 `P-Level` 구간(`SL/IL/DL`)은 큐레이션/설명 자료에서 확인되지만, 운영 코드에서 불변 공식으로 확정된 근거는 제한적이다.
- [VISION] 내부 의사결정 보조 프레임으로 활용하되, 외부 브리프에서는 "연구/설명 레이어"라고 명시하는 것이 안전하다.

### 4) 무손실 복원 제약/ECC
- [FACT] RS/ECC 완전 통합은 현재 미확정이다.
  - 근거: `scripts/run_mkm_l1_parity_prototype.py` (`This is NOT Reed-Solomon.`)
- [HYPO] `Lambda(x)S(x)=Q(x)x^t+Omega(x)`를 근거로 "현 시스템에서 100% 복원 달성"이라고 단정하면 환각 위험이 크다.
- [HYPO] RWKV 식(`w_t`, `wkv_t`)으로 현재 L2 엔진의 실시간 보장을 확정하는 것은 근거 부족이다.
- [HYPO] GD-RIPOR 손실식을 "현재 운영 적용 완료"로 단정할 수 없다.

### 5) 결론 교정
- [FACT] 현재 단계의 안전한 결론은 "하이브리드 구조 + 연구 격리 + 단계적 검증"이다.
- [HYPO] "사원수+RS 역연산으로 결정론 복원이 이미 완성"이라는 문장은 현 시점에서는 과장이다.
- [VISION] 장기 목표로 결정론 복원 정확도를 높이는 연구는 계속 가능하되, 대외 문구는 FACT/HYPO 분리를 유지한다.

---

## H) 수학 헌법 FACT-LOCK 표 (운영용)

- 분리 SSOT: `docs/final/MKM12_MATH_CONSTITUTION_FACT_LOCKED_V2.md`

| 항목 | 현재 등급 | 운영 문구(고정) | 승격 조건 |
|---|---|---|---|
| L0/L1/L2 계층 프레임 | **FACT** | 연구/운영 분리형 계층 프레임은 존재하며 체인에 반영됨 | 유지(변경 시 체인/브리프 동시 갱신) |
| 사원수 기본 법칙 (`i^2=j^2=k^2=ijk=-1`) | **HYPO 후보** | 수학적으로 타당하나 운영 복원 엔진의 직접 증명식으로 단정 금지 | 운영 경로 호출 + 테스트 통과 + 산출 JSON |
| S-L-K-M 매핑식 (`q=S+Li+Kj+Mk`) | **HYPO 후보** | 설명 모델식으로 사용 가능, 전역 구현식 단정 금지 | 코드 심볼/입출력 계약/회귀 테스트 |
| 사원수 합성곱 행렬 전개식 (`W⊗X` 해밀턴 행렬) | **HYPO 후보** | 연구식으로 인용 가능, 현행 운영 핵심식 단정 금지 | 실제 런타임 호출 경로 + 성능/정합 벤치 |
| 비선형 동역학 단일식 (`dx/dt=F+G+H+xi`) | **HYPO 후보** | 개념적 설명 레이어로만 사용 | 운영 지배식 코드 경로 + 파라미터 명세 고정 |
| ICD-DCV / P-Level 공식 | **HYPO 후보** | 분석 프레임으로 제한 사용, 프로덕션 불변식 단정 금지 | 계산기 코드 + 임계값 테스트 + 문서 고정 |
| LongLLMLingua 예산식 (`tau_k^doc`) | **HYPO 후보** | 후보 수식으로만 유지 | 구현 스크립트 + 입력/출력 아티팩트 + 회귀 |
| RWKV 감쇠식 (`w_t`, `wkv_t`) | **HYPO 후보** | 아키텍처 후보 근거로 제한 사용 | L2 실제 경로 적용 + 지연/메모리 실측 보고 |
| GD-RIPOR 제약 빔 서치 손실 | **HYPO/보류** | 운영 핵심 헌법에서 제외(또는 연구 주석) | 비용/지연 게이트 통과 실측(재현 필수) |
| RS 완전 복원식 (`Lambda(x)S(x)=...`) | **VISION** | 장기 목표 수식, 현재 운영 팩트 아님 | RS 실구현 + 오류주입 복원 벤치 + 게이트 통과 |

### 운영 규칙 (요약)
- **FACT 표기 조건:** 저장소 경로 + 실행 가능한 스크립트 + 재현 산출물(JSON/로그) 3요건 충족.
- **HYPO 표기 조건:** 수학/논문 타당성은 있으나 운영 경로 입증 미완.
- **VISION 표기 조건:** 장기 지향(미구현/미통합)으로 명시하고 운영 단정 금지.

---

## I) 외부 문헌 대조·내부 Fact-Lock 확정 (2026-04-10)

### I.1) 외부 기술 수치 (원문 PDF·표 기준, MKM12 코드 통합과 별개)

아래는 **타 연구·산출물**에서 확인된 인용용 앵커이다. **MKM12 저장소에 동일 구현이 있다는 뜻이 아니다** (통합·승격은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 호출 가능 스크립트로만 판정).

| 구분 | 앵커 | 비고 |
|------|------|------|
| Nacrith | arXiv:2602.19626 | enwik8 **0.9389 bpb**, OOD 예시 **0.723 bpb**, Canterbury alice29 **0.918 bpb** 등 (표·환경은 원문 따름) |
| L3TC | AAAI 2025; arXiv:2412.16642 | RWKV·outlier-aware; 처리량 **A100 4.35 MB/s**, **iPhone 12 1.30 MB/s** 등 (원문 표) |
| LLMLingua / LongLLMLingua | Jiang et al., 2023–2024 | 프롬프트 압축·토큰 절감·다운스트림 지표는 논문 버전별 상이 |
| SynCode | (해당 논문·리포) | JSON 등 제약 생성 정확도·지연 (원문 벤치) |
| RL-UEP | (해당 논문) | 엔티티 보존 등 (원문 수치) |
| LLMc | UW SyFI Lab 계열 | 순위 기반 무손실 텍스트 압축·오픈소스 (레포명·커밋은 인용 시 고정) |

### I.2) 내부 SSOT 표준 인용 (에이전트·브리프용)

- **역추론(빔) 평균 복원율:** `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json`의 `aggregate.avg_exact_restore_rate` — 항상 동일 파일의 `generated_at_utc`, `scoring_mode` (현재 스냅샷: `legacy`), `research_only`를 함께 인용.
- **사이드 채널 1.0 (연구 하네스, 오프-HTTP):** `scripts/run_l1_permutation_channel_integrated_spike.py` — **사이드 메타데이터가 완전할 때**만 `exact_restore_rate = 1.0`; 산출 `docs/final/artifacts/l1_permutation_channel_integrated_spike_latest.json`(스키마 v3). LLM 빔 역추론·서비스 전 구간 보장과 **구분**.
- **L1 사이드 채널 와이어 코덱 (라이브러리 팩트):** `scripts/l1_side_channel_wire_codec.py` — 적응형 msgpack(± zstd) 바이트열 인코딩; 하네스·스텁이 공통으로 호출 가능.
- **HTTP 연구 스텁 엔드포인트 (토큰 압축 API v1 스텁 위에 additive):** `POST /v1/research/l1_side_channel/wire` in `scripts/compression_token_api_stub.py` — 페이로드의 `side_channel`에서 최소 필드만 추출해 와이어를 base64로 반환; **상용 `POST /v1/compress`·`expand` 계약·프로덕션 SLA와 동일시 금지**. 계약 SSOT: `docs/final/openapi_token_compression_stub_v1.yaml` **v1.1.0+** (`L1SideChannelWireRequest`/`L1SideChannelWireResponse`). 팩트 락 표: `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §2 (토큰 압축 스텁·OpenAPI 행).
- **“Hybrid Guardrail” 같은 통칭**은 레포 단일 모듈명이 아니다. 운영·연구 게이트를 서술할 때는 예: `scripts/run_notebook_compression_full_chain.ps1` (일일 브리프·위생 JSON), `scripts/run_compression_weekly_governance_chain.ps1` (압축 거버넌스), `scripts/check_mkm_l1_rs_policy_gate.py` (RS 정책 게이트), Track A 계량·밴드: `scripts/check_track_a_metering_band_gate.py` 등 **호출 가능 경로**를 사용한다.

### I.3) 컴포넌트 (xxHash·MessagePack 등)

범용 벤치 성능은 문헌·업계 상식 수준으로 인용 가능하나, **MKM12 사이드 채널 JSON(와이어 프록시) 실측·프로덕션 통합 후**에만 내부 [FACT]로 승격한다. **msgpack/zstd 적응형 와이어·스파이크 v3·스텁 엔드포인트**는 “연구 레인 실측 + 스텁 노출”까지이며, **운영 SLA·대외 ‘무손실 압축 제품’ [FACT]로의 승격**은 별도 게이트로 본다. **스텁 HTTP:** `POST /v1/research/l1_side_channel/wire`는 서버에 **msgpack 미설치**이거나 내부 pack이 불가할 때 **503**을 반환할 수 있다(`compression_token_api_stub.py`); 파트너/에이전트 브리프에서는 pilot §10(`COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` §10)과 동일 경계를 유지한다.
