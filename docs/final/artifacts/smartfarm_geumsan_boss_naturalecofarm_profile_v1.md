# 금산 사장 · 자연생태농원 프로필 v1

| 필드 | 값 |
|------|-----|
| schema | `smartfarm_geumsan_boss_naturalecofarm_profile_v1` |
| status | `internal_ops` |
| SEND_GATE | **HOLD** (대외·보조금·가입 카피 복붙 금지) |
| generated_at_utc | `2026-07-17` |
| crawl_method | WebFetch(블로그 메인·logNo) + WebSearch + MKM SSOT 교차 |
| primary_blog | https://blog.naver.com/ecofarm62 |
| secondary_blog | https://blog.naver.com/naturalecofaram |

**라벨:** `[BLOG FACT]` 원문 · `[BLOG CLAIM]` 마케팅·성과 주장 · `[MKM SSOT]` 디스크 정합 · `[VERIFY]` 미확정.

---

## 1. 엔티티 정리

| ID | URL | 블로그명 | 관측 |
|----|-----|---------|------|
| **ecofarm62** | https://blog.naver.com/ecofarm62 · [모바일](https://m.blog.naver.com/PostList.naver?blogId=ecofarm62) | 자연생태농원 | **최신 본선** — 2026-07 위탁재배·하스카프 계약·두릅·귀농 스마트팜 (누적 조회 ~3.2만) |
| **naturalecofaram** | https://blog.naver.com/naturalecofaram · [모바일](https://m.blog.naver.com/PostList.naver?blogId=naturalecofaram) | 자연생태농원 | **구/병행** — 송이·능이·복분자·시험농장 (누적 ~10.1만, 이웃 ~1,583) |

**관계 `[VERIFY]`**

- 브랜드·소개문·문의번호(`010-4844-8500`)·법인명(**주) 자연생태농원 농업회사법인**)이 **양쪽에서 공유** → 동일 운영 주체로 **강하게 추정**.
- ecofarm62 최신 계약글에 **농협 계좌·법인 입금 명의**가 노출 → B2C 계약·수납 채널은 **ecofarm62 우선**.
- naturalecofaram은 송이·능이 등 **임산물 직판**과 구(2025) 시험농장 서사가 많고, ecofarm62가 **2026-07 계약 조건 SSOT**.
- **블로그 ID만 다른 이중 채널** (도메인 오타 `naturalecofaram` = natural eco **farm**).

**크롤 제약:** PostList·PC 프레임은 로그인 유도 UI. **개별 logNo 모바일/PC URL·메인 최신글 embed는 본문 추출 가능.** RSS는 2026-07-17 시점 500 오류.

---

## 2. 대표 / 운영자 프로필

| 항목 | 값 | 라벨 |
|------|-----|------|
| 브랜드 | **자연생태농원** | `[BLOG FACT]` |
| 법인 | **주) 자연생태농원 농업회사법인** (입금 명의) | `[BLOG FACT]` — [계약 세부](https://m.blog.naver.com/ecofarm62/224349346070) |
| 대표 실명 (블로그) | **미기재** | `[BLOG FACT]` |
| 대표 실명 (MKM 서류) | **이기륜** — 농업경영체·임차인·임업후계자 서류 | `[MKM SSOT]` — `smartfarm_business_plan_commander_pack_v1_latest.md` (블로그와 **교차 미검증**) |
| 휴대폰 | `010-4844-8500` (문자·계약 성립) | `[BLOG FACT]` |
| 유선 | `041-753-3677` (현장 방문·불편) | `[BLOG FACT]` — [송이글](https://blog.naver.com/naturalecofaram/223553523421) |
| 입금 | 농협 `351-1346-4059-23` / 주) 자연생태농원 농업회사법인 | `[BLOG FACT]` — **내부만, 대외 재게시 금지** |
| 포지셔닝 | 토착미생물·탄화숯·무화학 자연생태농법 · 직장인 제2수입 · **AI+CCTV 원격 위탁재배 원스탑** · 귀농·임산물 직판 | `[BLOG FACT]` / `[BLOG CLAIM]` |

---

## 3. 사업 모델

### 3.1 시험농장 100평 위탁재배 (핵심)

출처: [소개 2026-07-12](https://m.blog.naver.com/ecofarm62/224344232779) · [계약 세부 2026-07-17](https://m.blog.naver.com/ecofarm62/224349346070)

| 항목 | 내용 |
|------|------|
| 상품 | 재배지 **~100평 무상** + 하스카프 3년생 **60주** 위탁재배 |
| 총액 | **300만 원** (= 묘목 실물비 구성 명시) |
| 결제 | 계약금 **150만**(당일) + 잔금 **150만**(**2026-09-10**) · 입금 후 성함 문자 → 계약 성립 |
| 계약서 | **없음** — 블로그 글 카피 보관 = 이행 |
| 1차 기간 | **2026-10-15 ~ 2028-06-30** (식재 10/10~10/30) |
| 작물 선택1 | 하스카프 3년생 60주 × 5만 = 300만 |
| 작물 선택2 | 하스카프 50주(250만) + 신구두릅 100주(30만) + 토종복분자 100주(20만) |
| 관리비 | 명목 **150만** — 책임판매 시 수확대금 **40%** 차감(150만 상한, 미달 시 추가청구 없음) / 직접수확 **20%** |
| 연장 | 2~5차 각 1년 · 관리비 150만 중 **75만 선입** + 수확대금에서 75만 차감 · 종료 시 화분묘목 **120→360주** 증식 반환 |
| 종료 | 재계약 없이 종료 시 3년생 화분 **120주**(60주의 2배), 화물 **착불 고객** |

### 3.2 스케일 단계 `[BLOG CLAIM]`

| 단계 | 규모 | 내용 |
|------|------|------|
| 1 | **100평** 시험농장 | 수익·원격 재배 검증 |
| 2 | **1,000평+** 본농장 | 위탁운영 · 「본업 유지 + 고소득」 |
| 3 | **5,000평** 관광체험농원 | 전업·6차 산업 |

### 3.3 기타 수익축

- **묘목·종근** 판매 (하스카프·신구두릅 예약)
- **임산물** 송이·능이 직판·산림조합 입찰 수매 (스마트팜과 **별 레인**)
- **가공** 원액·잼·냉동생과 책임판매 서사
- **본농장 CAPEX** 임업후계자 선발 시 시설 **50% 무상보조** 안내 `[BLOG CLAIM]`

---

## 4. 현장 · 부지

### 4.1 계약글(2026-07-17) 식재 후보 1~5농장

| # | 리·필지 | 면적 | 라벨 |
|---|---------|------|------|
| 1 | 금성면 **파초리** 2필지 | 5,000평 | `[BLOG FACT]` |
| 2 | 금성면 **두곡리** 1필지 | 900평 | `[BLOG FACT]` |
| 3 | 두곡리 4필지 | 2,500평 | `[BLOG FACT]` |
| 4 | 두곡리 1필지 | 1,300평 | `[BLOG FACT]` |
| 5 | **상가리** 1필지 | 2,000평 | `[BLOG FACT]` |

### 4.2 소개글(2026-07-12) 1~12농원 서술

- 두곡리·상가리 **제1~12농원 합계 ~18,000평**, 개별 **1,000~5,000평**, **사질토(마사토)**. `[BLOG FACT]`
- 예: 1번 두곡리 5,000평(야산 기슭·경사) / 3번 2,500평(1번 인접 ~500m) / 12번·4번 상가리 인근 1,300~2,000평 — **연결된 야산 기슭 밭군**.
- **번호·리명 불일치:** 07-12 글의 「1번=두곡리 5,000평」 vs 07-17 글의 「1농장=파초리 5,000평」 → `[VERIFY]` 지번·임대 SSOT는 등기·임대차만.

### 4.3 MKM 현장 교차 `[MKM SSOT]`

| 항목 | MKM 서류 |
|------|----------|
| 임차 필지 | 충남 금산군 금성면 **상가리 179-1** · **2,019평** |
| 임대인 | 안동권씨화천군파종중·정헌공파종중 (**종중**) |
| 임차인 | **이기륜** · 2026-05-01 ~ 2031-04-30 · 연 100만 원 |
| FaaS 파일럿 | Phase 1 **~300평** · 6채널 IoT (`smartfarm_geumsan_faas_master_plan_v10_lite_v1.md`) |

블로그 5농장(상가리 2,000평)과 MKM 임대(상가리 179-1, 2,019평)의 **동일 필지 여부 `[VERIFY]`**.

---

## 5. 스마트팜 · AI · CCTV vs MKM Fact-Lock

| 블로그 주장 | 라벨 | MKM 경계 |
|-------------|------|----------|
| 「학습된 AI가 수분·미생물·영양 **자동** 공급」 | `[BLOG CLAIM]` | ML/LLM 자동관수 **미구현** — 노지심 = 센서·**원격 On/Off**·안전 인터록·일지 |
| 「스마트폰 하나로 **완벽** 원격 경영」 | `[BLOG CLAIM]` | 월 1~2회 **현장 방문·실경작** 권장/약관 (`smartfarm_geumsan_subscriber_brochure_v1.md`) |
| CCTV 전과정·회원 자료실 | `[BLOG FACT]`/`[BLOG CLAIM]` | UX 참고 가능; MKM이 **수확·판매 보장** 금지 |
| 전문가 잡초·병해충·전정 | `[BLOG FACT]` (역할 선언) | **사장 노동 축** — 플랫폼이 대체 주장 금지 |
| 「고소득 연봉·본업 능가·블루오션」 | `[BLOG CLAIM]` | 보조금·IR·대외 카피 **금지** (`smartfarm_public_copy_factlock_v1.md`) |
| 「AI 스마트팜 **무상** 제공」 | `[BLOG CLAIM]` | IoT = **사장 CAPEX**; MKM 앱·브릿지는 **별도 B2B/B2C** |

---

## 6. 6차 · 체험 · 가공

| 축 | 블로그 내용 | 라벨 |
|----|-------------|------|
| 1차 판매 | 원물생과 · 원액 · 잼 · 냉동생과 · 분말 | `[BLOG FACT]` |
| 체험 | 하스카프 **수확 체험** · 주말·가족 단위 관광농원 적합 서사 | `[BLOG CLAIM]` |
| 카페 | 체험농원 내 **요거트 스무디** 등 가공 메뉴 | `[BLOG CLAIM]` |
| 6차 로드맵 | 재배→체험→가공(잼·원액·와인)·**5,000평 관광농원** | `[BLOG CLAIM]` |
| 복분자 | 전량 수매·즙·양강·식초·와인·온라인 자립 | `[BLOG CLAIM]` — naturalecofaram |
| 임산물 | 송이·능이 = **커머스·입찰** (6차와 분리) | `[BLOG FACT]` |

MKM 관광농원·모듈러 숙박은 `athena_autonomous_garden_business_plan_v2_3_latest.md` — **블로그 약한 언급과 합선 금지**.

---

## 7. MKM · 지휘관과의 관계

| 축 | 자연생태농원(사장) | MKM |
|----|-------------------|-----|
| **임대차** | 블로그 농원 다필지·위탁재배지 | **종중→이기륜** 상가리 179-1 `[MKM SSOT]` |
| **CAPEX** | 묘목·두둑·IoT·배관·300만 상품 | **0원** — SW·센서 연동만 |
| **B2C 가격** | **300만** 위탁(묘목+재배+판매 서사) | 보증금 300만(사장) + 가입 150만 + 월 99k `[MKM SSOT]` |
| **B2B** | 설치·턴키·현장 노동 | 노지심 SaaS·6ch 제어·일지 |
| **행정** | 임업후계자·50% 보조 **고객 안내** | 양식·체크리스트만 — **결과 미보장** |

**협력:** 동일 금산 권역 · 하스카프·두릅·복분자 · 하이브리드(원격+전문가) 서사.  
**경쟁/충돌:** 사장이 이미 「AI+CCTV+300만 원스탑」을 **단독 B2C 판매** → 팜팜팜/MKM이 동일 카피 시 **채널 충돌·이중 과금·과대광고** 리스크.

---

## 8. 리스크 · Fact-Lock (MKM이 베끼면 안 되는 문구)

1. **「AI가 알아서 진단·급수·영양」** — 공개·보조금·가입 카피 금지.
2. **「고소득 연봉·본업 능가·안전한 소득」** — 수익 보장형 표현 금지.
3. **「계약서 없이 블로그만」** — MKM 약관·임대차와 **양립 불가** (법무).
4. **블로그 300만 ≠ MKM 150만+월99k+보증300** — 숫자 합선 사고.
5. **농원 번호·리명 불일치** (파초 vs 두곡 1번) — 제출 전 `[VERIFY]`.
6. **계좌·휴대폰** — 내부 프로필만.
7. **50% 보조·임업후계자** — 블로그 영업 ≠ 군·산림청 공고 Fact-Lock.
8. **화학 무사용** — 인증·검사 첨부 없음; MKM이 **인증 보장** 금지.

---

## 9. 출처 URL 목록

### 접근 방법

| 방법 | 결과 |
|------|------|
| WebFetch `blog.naver.com/ecofarm62` | OK — 최신 계약글 embed |
| WebFetch `blog.naver.com/naturalecofaram` | OK — 능이버섯 글 embed |
| WebFetch `m.blog.naver.com/ecofarm62/224344232779` | OK — full text |
| WebFetch `m.blog.naver.com/ecofarm62/224349346070` | OK — full text |
| WebFetch PostList (양쪽) | 소개문 OK · 글 목록 로그인 UI |
| WebSearch `site:blog.naver.com` | 관련 글 직접 hit 제한적 |
| RSS | 500 오류 (2026-07-17) |

### ecofarm62 (우선)

1. https://m.blog.naver.com/ecofarm62/224349346070 — AI 스마트팜 100평 위탁 계약 세부 (2026-07-17)
2. https://blog.naver.com/ecofarm62/224349346070 — PC 동일
3. https://m.blog.naver.com/ecofarm62/224344232779 — 300만 위탁 소개·12농원·6차 로드맵 (2026-07-12)
4. https://blog.naver.com/ecofarm62 — 메인(최신글 embed)
5. https://m.blog.naver.com/PostList.naver?blogId=ecofarm62 — 소개·카테고리

### naturalecofaram

6. https://blog.naver.com/naturalecofaram — 메인
7. https://blog.naver.com/naturalecofaram/223553523421 — 2025 송이버섯 시세·직판 (2024-08-19)
8. https://m.blog.naver.com/PostList.naver?blogId=naturalecofaram — 소개(금산 명시)
9. https://m.blog.naver.com/naturalecofaram/223774012365 — 300만 시험농장 (2025, 교차)
10. https://m.blog.naver.com/naturalecofaram/223782570361 — 복분자 수매 (교차)
11. https://m.blog.naver.com/naturalecofaram/224023027485 — 능이·송이 (교차)

### MKM 교차 SSOT

- `docs/final/artifacts/smartfarm_geumsan_artifact_index_v1.json`
- `docs/final/artifacts/smartfarm_geumsan_faas_master_plan_v10_lite_v1.md`
- `docs/final/artifacts/smartfarm_business_plan_commander_pack_v1_latest.md`
- `docs/final/artifacts/smartfarm_geumsan_forestry_two_track_business_plan_v1.md`
- `docs/final/artifacts/smartfarm_public_copy_factlock_v1.md`

---

**한 줄:** 자연생태농원(ecofarm62)은 금산에서 **「300만 묘목+위탁+AI/CCTV 마케팅」을 이미 단독 B2C**로 판매 중이며, MKM은 **노지심·팜팜팜·V10 정산**을 얹되 **AI·수익보장·블로그 계약 조건을 복제하면 안 된다.**
