# MKM 스마트팜 사업계획서 — 지휘관 팩 v1 (별도 SSOT)

- **schema:** `smartfarm_business_plan_commander_pack_v1`
- **generated_at_utc:** 2026-07-15T01:09:16Z
- **status:** `internal_ops` · **research_only** · **SEND_GATE: HOLD**
- **purpose:** 금산 노지 스마트팜·기술현황·지휘관 인적/자격 상황을 **한 문서**로 보관 (기존 V10-lite·관광농원 v2.3·NL06과 병행, 대체 아님)
- **lanes:** Web-Ops / Track C 내부 · **Track A·실매매·대외 SEND 금지**
- **NL notebook:** `06-2026q2` · `05 · 금산 스마트팜` · https://notebooklm.google.com/notebook/96865180-769e-4a77-89bb-5f03a8083ac3
- **NL session:** `1211c70e` (2026-07-15) — 답변은 **[NL-HYPO]** · 공부 원본 PDF와 대조 필수

---

## 0. Executive one-pager

| 항목 | 내용 |
|------|------|
| **모델** | 노지 **관수 IoT(큐빅스 CoCoNET) + MKM SW/안전 게이트/일지(FaaS)** — 억대 식물공장 턴키 **아님** |
| **현장 Phase 1** | 충남 금산 · **~300평 관수 파일럿** · 목표 **6ch** · 계약·견적 **3ch 330만 VAT포함 확정** · 6ch 수정견적 대기 |
| **법인** | (주)목소리네트워크 · 대표 이기륜 · 본점 광명시 광명로 880 |
| **현금(포트폴리오)** | 주 cash cow는 **a-codeai** · 스마트팜은 **파일럿·SI·(가설)FaaS** — 본업과 합선 과장 금지 |
| **성숙도** | pre-Go-Live · 가입자 0 · 현장 E2E KPI 미통과 |
| **대외 포지션** | 「노지 관수 소프트웨어 파트너」 (`smartfarm_public_copy_factlock_v1.md`) |

---

## 1. 지휘관 현황 (인적 · 사업 · 자격)

### 1.1 의료 · 거점 [DISK]

| 항목 | 값 | 근거 |
|------|-----|------|
| 클리닉 L0 | **광명백제한의원** | `jmkm_clinical_brand_layers_v1_latest.json` · intake kit · PUBLIC identity |
| 역할 | 한의사 원장 · 겸업 창업자 | 지휘관 운영 사실 · NL 겸업 의료인 참고소스는 있으나 **한의원 증서 PDF는 NL06에 없음** |
| 법인 겸업 맥락 | 수도권 거주 겸업 의료인의 농업 진입 · 회사 대표 겸직 | NL06 참고 아티클 제목만 존재 — **법률 자문 [VERIFY]** |

### 1.2 법인 · 주소 [NL 소스 요약 · 공부 대조]

| 문서 (NL 제목) | 핵심 팩트 |
|----------------|-----------|
| 등기사항전부증명서 | **주식회사 목소리네트워크** · 대표이사 **이기륜** · 사내이사 조영임 · 자본금 **1,000만 원** · 본점 **경기도 광명시 광명로 880** · 회사성립 2020-12-23 · 증명 발행 표기 2026-05-08 |
| 사업자등록증명(법인) | 동일 법인 · 개업 2021-01-05 · 등록 2021-01-08 · 발급 표기 2026-06-12 · 광명로 880 |

### 1.3 농업 · 농지 [NL 소스 요약 · 공부 대조]

| 문서 | 핵심 팩트 |
|------|-----------|
| **농지임대차계약서** | 임대인: 안동권씨화천군파종중·정헌공파종중 · 임차인: **이기륜** · 기간 **2026-05-01 ~ 2031-04-30** · 연 임차료 **100만 원** · 소재 **충남 금산군 금성면 상가리 179-1** · 면적 **2,019평** |
| **농업경영체 등록(변경) 확인서** | 경영주 **이기륜** (생년월일 표기 73.12.10) · 발급/등록일 **2026-06-19** · 주민등록지 광명시 디지털로 24, 102동 2301호 · **실경작지 상가리 179-1** · 의미: **경영주=농업인 등록 확인** |

### 1.4 임업후계자 [NL 소스 요약 · 공부 대조]

| 항목 | 내용 |
|------|------|
| **NL 소스** | IMG_2026-07-15T10-07-17.155515.jpg (임업후계자증서 스캔) · 업로드 확인 2026-07-15 |
| **성명** | 이기륜 (생년월일 표기 1973. 12. 10.) |
| **지정일** | **2026년 7월 9일** |
| **지정번호** | **제 2026 - 7 호** |
| **발급** | 충청남도 **금산군수** · 「임업 및 산촌 진흥촉진에 관한 법률」 제2조제4호 의거 (NL 요약) |
| **상태** | **NL 실물 확인** · 원본과 대조 후 대외·보조금 문서에만 **[FACT]** 승격 · 보조금 비율·합격 **미보장** |

※ 이전 [COMMANDER_ASSERT · VERIFY](스캔 미업로드)는 **해제**. NL 문구의 「50% 무상 보조금 프리패스」류는 **대외 금지**(공고 PDF [VERIFY]만).

### 1.5 주소 레이블 주의

- NL·임대차·경영체: **금성면 상가리 179-1**
- 구 디바이스 매니페스트 일부: 「의신면」표기 — **동기화 필요**. Go-Live·대외는 **공부(임대차·경영체) 주소**를 승.

---

## 2. 금산 스마트팜 현장 · 기술 현황

### 2.1 물리 · 채널 (디스크 SSOT)

| 항목 | 상태 |
|------|------|
| Phase 1 범위 | 노지 점적 · 약 **300평** 관수 파일럿 · FaaS는 앱상 **가상 10구획 / 물리 4작물·6ch** |
| 채널 맵 | ch1 맹물 · ch2 양액 · ch3 노지 두릅(~200평) · ch4 화분커피 체험(~20평) · ch5 잎들깨 · ch6 계절체험 (`6channel_valve_mapping`) |
| 커피 정책 | 상업 「코나·100평」**폐기** · 데모·체험만 · 동절기 실내 대피 |
| CAPEX 주체 | **금산 사장** 선투자 · **MKM CAPEX 0** (SW) |
| B2C 가격 | 보증금 300만(사장) + 가입비 **150만** + 월 **99,000** · Premium 폐기 |

### 2.2 큐빅스 계약 · 장비 [FACT disk + NL]

| 항목 | 값 |
|------|-----|
| 벤더 | (주)큐빅스 · CoCoNET |
| 서명 견적 | **260522 3ch** · **3,300,000원 VAT포함** (공급 300만+부가세 30만) |
| 이전 견적 | 260520 · NL 표기 **4,950,000원** → 최종 3ch로 정리 |
| 납품 BOM (목표 6ch 구성) | GW **G300** · 토양 **D301/D302** · 릴레이 **D202(6ch)** · 밸브 40mm×6 · 망 N300 / group `smartfarm` |
| 설치 | **고객 자가설치** · 1년 AS(택배) · 현장출장 별도 |
| 6ch | 지휘관 확정 · **수정 견적 PDF 대기** (`quote_final_note`) |
| 현장 E2E | **blocked** — cid commission · VPS broker · live ACK 대기 |

### 2.3 MKM 소프트웨어 성숙도

| 기능 | 상태 |
|------|------|
| HTTP ingest · Phase0 dry-run | **pass** (스크립트 체인) |
| MQTT subscriber · uplink dry-run | 스크립트 ready · **live broker/cid TBD** |
| 안전 정책 YAML (동시 OPEN·stale·런타임) | 문서·stub 경로 **부분** · 현장 미증명 |
| 운영자 PWA | 코드 경로 존재 · **완성 주장 금지** |
| 작물 ML / LLM 관수 | **missing / 직결 금지** |
| 가입자(FaaS) | **0** |
| Go-Live KPI (72h 통신≥95% · ACK≥99% · 30일 인터록 0) | **미측정** |

### 2.4 경쟁 위치 (갭 SSOT 한 줄)

> MKM은 하드웨어·ML·LLM에서 이기지 못함. **FaaS 행정 레이어+안전 게이트를 현장 KPI로 증명**해야 함.  
> (`smartfarm_competitor_capability_gap_v1.json`)

---

## 3. 사업 모델 · 수익 구조

### 3.1 B2B SI (노지 관수 SW)

- 가치: 검증 IoT API 연동 · 안전 게이트 · 불변 로그 · (선택) 일지/PDF
- 가격 감각: IoT 키트 **수백만** (3.3M 밴드) + MKM 온보딩/월 — **억 단위 CAPEX 판매 아님**
- 수요: 노지 스마트화는 시설대비 **초기·얇음** · 구매력은 통합 HW사에 기울어 있음 · 우리 니치는 **반쪽 턴키+컴플라이언스/로그** [HYPO]

### 3.2 B2C FaaS (V10-lite · 가설)

| | 10구획 풀가동 **시뮬레이션** |
|--|------------------------------|
| 가입비×10 | 1,500만 (MKM 900 / 사장 600) |
| 월구독×10 | 99만/월 (MKM 50 / 사장 49) |
| 보증금 | 사장 수납·반환 |
| 상태 | **설계·약관 초안** · 실가입 **0** · 자격/세무 **미보장** |

### 3.3 확장 [HYPO] (본 팩 범위 밖 상세)

- 금산 관광농원 ~2,000평 · 진도 만길리 ~1만평 → `athena_autonomous_garden_business_plan_v2_3_latest.md` §8
- 본 팩은 **Phase 1 금산 IoT+자격 기반**에 초점

---

## 4. 기술력 주장 경계 (Fact-Lock)

### 허용 (KPI 전 · 내부)

- 큐빅스 파트너 하드웨어 + MQTT/HTTP 연동 **PoC·dry-run 통과**
- 안전 정책·밸브 맵·FaaS 상품 설계 문서화
- 경영체 등록·농지 임대차·법인 공부 **행정 베이스 확보** (NL 소스)

### 금지 (현재)

- 「AI 스마트팜 완성」「LLM 자동관수」「수확·소득 보장」「업계 우위」
- 임업후계자를 **공부 확인된 사실**처럼 대외 기재 (스캔 미업로드)
- 가입자·현장 KPI 없는 **상용화 완료** 선언

### KPI pass 후 허용 문안 (목표)

- 금산 파일럿 72h 통신안정률 · 6ch ACK · 30일 인터록 0 — 기간 명시 (`golive_kpi_minimum`)

---

## 5. 로드맵 (다음 1타급)

1. **6ch 수정 견적 PDF** 수신 · 계약 아티팩트 갱신  
2. **현장 배선·G300·cid commission** · VPS Mosquitto  
3. Go-Live **KPI-1~3** 스크립트·측정  
4. NL06에 **임업후계자 지정서** 업로드 → §1.4 FACT 승격  
5. (선택) 사장 클로징 시트 미팅 · 가입자 약관 세무 검토  
6. FaaS 영업은 **1–5 이후** — PMF 전 확대 금지

---

## 6. 연계 SSOT 인덱스

| 문서 | 경로 |
|------|------|
| FaaS 마스터 | `docs/final/artifacts/smartfarm_geumsan_faas_master_plan_v10_lite_v1.md` |
| 아티팩트 인덱스 | `docs/final/artifacts/smartfarm_geumsan_artifact_index_v1.json` |
| 큐빅스 계약 | `docs/final/artifacts/smartfarm_qubics_contract_signed_v1.json` |
| 디바이스 | `docs/final/artifacts/smartfarm_qubics_device_manifest_v1.json` |
| 경쟁 갭 | `docs/final/artifacts/smartfarm_competitor_capability_gap_v1.json` |
| Go-Live KPI | `docs/final/artifacts/smartfarm_geumsan_golive_kpi_minimum_v1.json` |
| 대외 카피 | `docs/final/artifacts/smartfarm_public_copy_factlock_v1.md` |
| 관광농원·진도 | `docs/final/artifacts/athena_autonomous_garden_business_plan_v2_3_latest.md` |
| NL sync pack | `reports/notebooklm_smartfarm_geumsan_sync_pack_v1/` |
| 벤더 PDF | `reports/smartfarm_vendor_replies/` |
| 승인맵 | `reports/delegation_smartfarm_business_plan_pack_approval_map_v1_latest.json` |

---

## 7. Epistemic footer

- NL 답변 = **참고** · 숫자·자격 **승격은 PDF/공부와 교차** 후만.  
- 본 문서 ≠ PUBLIC SEND 승인.  
- 포트폴리오 One cash cow(a-codeai)와 **스마트팜 매출을 합산 과장하지 않음**.

---

## 8. Change log

| utc | change |
|-----|--------|
| 2026-07-15T01:09:16Z | NL06 임업후계자증서 스캔 확인 → §1.4 NL 요약·지정번호 반영 · COMMANDER_ASSERT 해제 · 보조금 과장 금지 유지 |
