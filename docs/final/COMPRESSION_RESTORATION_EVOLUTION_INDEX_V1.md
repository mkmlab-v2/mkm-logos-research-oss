# 압축·복원 핵심 기술 진화 인덱스 (v1)

**역할:** 지난 구간 동안 **레포에 남아 있는 근거**만으로, 압축·복원 스택이 어떤 순서로 두꺼워졌는지 한 번에 따라갈 수 있게 한다.  
**한계:** 이 파일은 **외부 노트·1년 전 채팅 로그를 재구성하지 않는다.** 연대기의 1차 근거는 **`docs/final` 문서 날짜·`docs/final/artifacts/*.json`·Git 커밋**이다. 다수 핵심 스크립트는 **2026-03-30 전후**에 본격 도입된 기록이 있다(그 이전 동일 경로의 히스토리가 없으면 “이 레포에서의 가시 구간”이 짧다고 보면 된다).

---

## 1) 한 줄 요약 — 무엇이 “진화”했나

| 축 | 과거(초기 구간) | 현재(팩트 락 기준) |
|----|-----------------|---------------------|
| **목표** | 단일 지표·감으로 “잘 압축” | **Track A/B·ultra-literal**로 목표 분리, **벤치 혼동 금지** (`FAIL-COMP-004`) |
| **라우팅** | (문서상) 파일럿 샤드 | **`codebook/shards/zone_*.json` 전역 로드** + 도메인 라우터 |
| **품질 검증** | 추상적 “멀티렌즈” | **`evaluate_report`** 중심의 절약·Jaccard·민감 무결성·품질 게이트 |
| **진단** | 사후 감각 | **`report_compression_jaccard_loss_patterns`**, 샤드 패치 제안, KPI 요약 체인 |
| **부가 레일** | — | **Master codebook lexicon V1** must_keep 보강, **게마트리아 4D 브리지**(실험·정책 플래그), **Trust Packet v2** 초안·스텁 |
| **대외·승격** | 스토리 위주 | **`COMPRESSION_12M_*` §9**, OpenAPI 스텁, P0 경로 게이트 — **연구→상용 합선 금지** 명문화 |

---

## 2) 시간순 “가시 구간” (Git·문서 타임스탬프 기준)

아래는 **이 저장소에서 추적 가능한 이벤트**를 압축 레인 관점으로 묶은 것이다.

### 2026-03-30 — 측정 프레임 고정

- **추가:** 측정 가능한 multilens 성능 평가 프레임, V2 샘플 확장 (`feat: add measurable multilens…`, `expand … V2`).
- **의미:** “말로 하는 복원 품질”이 아니라 **같은 함수·같은 입력 스키마 논의**가 가능해진 시점.

### 2026-03-31 — 울트라 벤치·B-track 게이트·런타임 강화

- **추가/개선:** ultra-compression 벤치·CI 일관성, 런타임 evaluator 개선, B-track 파일럿·베이스라인 락·월간 체인 연동.
- **의미:** **회귀 가능한 벤치**와 **연구 레인 격벽**이 같은 막에 올라옴.

### 2026-03-31 — Master codebook lexicon 브리지

- **`evaluate_report`**에 master codebook lexicon V1 브리지 — `must_keep` 보강(lexicon rail).

### 2026-04-02 ~ 04-04 — 투트랙 SLA·손실 진단·SSOT 뭉치

- **SLA 정책** (`COMPRESSION_SLA_POLICY_V1.md`): Track A universal vs literal vs ultra-literal 역할·아티팩트 분리.
- **Jaccard loss 리포트**, literal/ultra 리포트, KPI 파이프라인 갱신.
- **해석 파이프라인 Fact-Lock** (`COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`) + CONSTITUTION/P0 정렬.

### 2026-04-03 이후 (Fact-Lock §6.1) — 절약 vs 무결성

- 무결성 우선 **must_keep 보강**으로 글로벌 절약률이 레거시 50% 미만일 수 있음 → **`ultra_saving_policy_ok`(0.49)** 등 이중 게이트.

### 2026-04-06 ~ 04-12 — 정밀·계약·데이터 흐름

- 게마트리아·multilens CLI·가설 배치 스키마 등 연구 쪽 확장.
- **ultra-literal** 연구 프로파일(Jaccard 극대화 목표, 비용·연구 경계는 SLA 참고).
- **Trust Packet v2** 스텁·탐색기·CI·P0 경로.
- **4D 브리지 정책 CLI** + V2 universal A/B 산출물.
- **`evaluate_report` 데이터 흐름** 단일 문서화 + 외부 ACON 문헌과의 **개념 매핑 v0**(동일 구현 주장 없음).

### 2026-04-08 — 12M 러닝 + 승격 체크리스트

- **`COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md`**: 시장 주장·벤치 순서·Track A 현실·Track B 쿼터니언 연구·**§9 승격** 등 “운영 철학” 정리.

### 2026-04-13 — AE-2 KOSPI 일간 수익률 구조 엔트로피 스파이크 (연구·관측 전용)

- **스크립트:** `scripts/spike_kospi_structural_entropy_v1.py` (합성 또는 `research/market_data/kospi_daily_external_yf.csv` 기반), `scripts/spike_kospi_structural_entropy_compare_v1.py` (G2 비교).
- **산출물:** `docs/final/artifacts/spike_kospi_kld_v1.json`, `spike_kospi_kld_v1_real.json`, `spike_kospi_kld_v1_compare.json` — 3-bin 대 균등 KL·SL-K-M 가설 투영 요약·zlib/zstd 바이트 대조.
- **격벽:** **멀티렌즈 토큰 압축·`evaluate_report` 본선과 자동 합선 없음.** **B-track blind replay** 코스피 그리드(`reports/constitution/btrack_pilot/blind_replay/*kospi*`)는 **별도 레일**(리플레이·스코어링) — AE-2와 동일 실험·동일 게이트가 **아님**.

#### Phase 3 — 역할 분리 (박제)

| 레일 | 목적 | 대표 경로·산출 | AE-2와의 관계 |
|------|------|----------------|---------------|
| **AE-2 스파이크** | 일간 단순 수익률 → ±1% 3-bin, KL(대 균등), `SlkmProjectionV1` 평균, `float64` 패킹 대 zlib/zstd 바이트 | `scripts/spike_kospi_structural_entropy_v1.py`, `docs/final/artifacts/spike_kospi_kld_v1_*.json` | 본 행 자체가 SSOT. |
| **Blind replay (B-track)** | 코스피 시계열에 대한 **블라인드 리플레이·그리드·스코어** 실험; promotion·월간 체인 등 **기존 게이트**와 연결될 수 있음 | `reports/constitution/btrack_pilot/blind_replay/*kospi*` 등 | **입력·지표·게이트가 AE-2와 다름.** AE-2 결과를 replay 승격·압축 KPI에 **자동 합선 금지.** |

#### 실측 베이스라인 스냅샷 (디스크 기준, CSV 갱신 시 변동)

- **근거 파일:** `docs/final/artifacts/spike_kospi_kld_v1_real.json` (`schema_version`: `spike_kospi_structural_entropy_v1`).
- **입력 CSV:** `research/market_data/kospi_daily_external_yf.csv`.
- **기간 (`csv_source_health`):** `first_date` **2024-04-11** — `last_date` **2026-04-10**; `return_pairs_computed` **484**; 스킵 **0**.
- **분포:** `kld_bin_vs_uniform_nats` **≈0.1363**; `structural_entropy_bits` **≈1.388**; `slkm_projection.mean_vector` S/L **≈0.233**, K/M **≈0.267** (가설 투영).
- **바이트 대조 (동일 스키마):** `zstd_compressed_bytes` / `raw_bytes` **≈0.929** (KLD·엔트로피와 **척도 다름** — 병합 서술 금지).

---

## 3) 읽기 순서 (통찰용 소스 묶음)

1. **정책·레일:** `docs/final/COMPRESSION_SLA_POLICY_V1.md`  
2. **런타임이 사실상 무엇을 하는지:** `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`  
3. **함수·플래그 순서:** `docs/final/COMPRESSION_EVALUATE_REPORT_DATA_FLOW_V1.md`  
4. **반복 금지(벤치 섞기 등):** `docs/final/MKM_LESSONS_LEARNED_V1.md`  
5. **상용·연구 경계·P0:** `docs/final/P0_COMMERCIALIZATION_TRACKER.md` (압축 절)  
6. **12M 메타 러닝 + 승격:** `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md`  
7. **대표 산출물 (숫자는 갱신 시 변동):**  
   - `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`  
   - `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json`  
   - `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json`  
   - `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json`  
8. **진입 스크립트:** `scripts/run_ultra_compression_default.py`, `scripts/run_ultra_compression_bench.py`, `scripts/run_compression_automation_chain.ps1`  
9. **(선택) H: 운영 메모:** 아래 §5 — **multilens 파이프라인 SSOT가 아니라** 병행 맥락용.  
10. **(선택) AE-2 시장 수익률 스파이크:** §2 `2026-04-13` 및 `docs/final/artifacts/spike_kospi_kld_v1_compare.json` — **압축 KPI·Track A 승격 근거 아님.**

---

## 4) 에이전트용 메모

- **“1년 전과 비교해서 코드가 이렇게 바뀌었다”**는 말은 **이 인덱스 + 위 문서**가 없으면 환각 위험이 크다.  
- 수치 비교는 **같은 입력 JSON·같은 모드·같은 아티팩트 파일**에서만 한다 (`FAIL-COMP-004`).  
- **16-state ↔ 압축 런타임 필수 배선**은 Fact-Lock상 **아직 아님** — 로드맵은 동 해석 문서·`STATE16_INTERFACE_INSERTION_CONTRACT_2026-03-31.md` 참고.  
- **AE-2 KOSPI 스파이크**와 **blind replay 코스피**는 §2 `2026-04-13` Phase 3 표대로 **역할이 다르다** — 한쪽 수치를 다른 쪽 게이트·승격 근거로 쓰지 않는다.

---

## 5) `H:\workspace` 병행 근거 (2026-04-12 실측)

**질문:** 과거 Git이 없어지면 H:에도 압축·복원 **엔지니어링** 연대기가 없을까?

| 점검 항목 | 결과 |
|-----------|------|
| **`H:\workspace\.git`** | **없음** — 루트는 Git 저장소가 아니므로 **커밋 타임라인·diff로 1년 진화를 재구성할 수 없다.** |
| **`H:\workspace\docs\` 규모** | 대량 Markdown(예: 2025-11~ 작업·전략·LoRA·배포 보고), `.our_memories`·`daily`·`archive` 등 **파일 기반 작업 기록** |
| **C:\workspace SSOT 문자열과의 겹침** | `run_ultra_compression` · `MULTILENS_ULTRA` · `codebook/shards` · `evaluate_report` 등을 **파일명·본문에서 일괄 매칭**했을 때 **해당 없음** (샘플 스캔 기준). 즉 H: 문서의 “압축”은 **다른 축**이 많다. |
| **대표 예시** | `docs\Rules_압축_완료_보고서_20251126.md` — Cursor **`.mdc` 규칙 파일 줄 수 축소**(라인 감소 %) 보고. 이는 **토큰 절약·Jaccard·도메인 샤드**를 다루는 `evaluate_report` **멀티렌즈 압축 레일과 동일 개념이 아니다.** |

**통찰 (합치기):**

- H:는 **에이전트 규칙 최적화·LoRA·배포·GraphRAG 등 “주변 운영”**의 밀도를 보여 준다.  
- **벤치·아티팩트·투트랙 SLA·게이트**로 정의되는 **압축·복원 핵심 기술**의 연대기는 **`C:\workspace` Git + `docs/final`**이 SSOT이며, Git 히스토리가 삭제된 경우 **H:만으로는 그 축을 복원할 수 없다** — 다만 **용어 혼동**(“압축” = 규칙 줄이기 vs 멀티렌즈 엔진)을 막는 데는 H: 샘플이 역할을 한다.

---

## 6) 갱신 규칙

- 분기마다 또는 **압축 런타임·SLA·Decision JSON 계약**이 바뀔 때: §2에 줄 추가, §3 링크 점검.  
- **`H:\workspace` 재점검:** 드라이브 구조나 Git 유무가 바뀌면 §5 표만 갱신한다.  
- 버전 범프: 본 파일명의 `_V1` 유지, 중대한 서술 변경 시 `V2` 새 파일 권장.
