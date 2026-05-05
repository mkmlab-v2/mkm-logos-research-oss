# Track C IP Business Plan (v2)

Date: 2026-05-05  
Revised: 2026-05-05 — **핵심이론 보호 상용화 가드(§9A)** 신설: `Model-as-a-Service` 분리, 공개/비공개 필드 경계, 계약/접근통제/워터마킹, 90일 실행 체크리스트를 Track C GTM에 편입. (이전: 2026-05-03 `§3.8` B2B 구독 파도 고정.)  
Owner: MKM core team  
Scope: `Track C (IP licensing and insight products)`를 중심으로, `초고난도 비정형 텍스트 스트레스 테스트/명리/사상/압축·토큰절감/신시장지표` 사업축을 우선순위 기반으로 통합 운영한다.

**SSOT / Freeze:** 본 문서는 레포 내 Track C 사업 계획의 **단일 진실 공급원(SSOT)**으로 **2026-05-05 재동결(FROZEN)** 처리한다. 이전 동결(2026-05-03) 대비 **§9A 신설**(핵심이론 보호·비공개 운영·계약/기술 통제), **§10** 실행항목에 보안 우선 액션 반영. 개정 시 상단 `Date`·`Revised`·본 문단에 **개정 사유·승인 범위**를 명시한다. `§3.7`은 영업·마케팅·개발 파이프라인의 **공통 지침**으로 적용한다.

## 1) Fact-Locked Baseline

- 분리 원칙: `Track A/B` 운영·연구 레일과 `Track C` 상용 패키징은 합선하지 않는다.
- 거버넌스/게이트는 경로와 아티팩트 기반으로만 주장한다. 브리핑 단독 주장은 금지한다.
- 법무 문구 고정:
  - `risk warning`
  - `Not investment advice`
  - `No guarantee of returns`
  - `Final decisions remain with client operators`
- **대외 단정 금지:** 관할·업종·표현에 따라 규제 해석이 달라질 수 있으므로 **「규제 회피 완료」「법적 리스크 제로」** 등 절대화 표현을 마케팅·제안서에 쓰지 않는다. 계약·랜딩 전 **법무 검토**를 절차로 둔다.
- **Evidence pack lock (검증 스크립트 정합):** `Not investment advice; final decisions remain with client operators.`

## 2) NotebookLM + 장기기억 연계 점검 결과

### 2.1 결론

- **연결 가능**: NotebookLM은 사업 아이디어 확장과 인사이트 수집에 유효하다.
- **체화 기준**: 장기기억 SSOT는 `docs/final/CENTRAL_AGENT_MEMORY_V1.md`와 Git 이력이다.
- **승격 조건**: NotebookLM에서 나온 내용은 반드시 레포 경로·아티팩트로 교차 검증 후 Track C 계획에 반영한다.

### 2.2 이번 개정에 반영한 원칙

- 즉시 매출화 후보는 `압축·토큰절감`을 1순위로 둔다.
- `초고난도 비정형 텍스트(성경·사해사본 등)/명리/사상`은 Track C에서 **리스크 포지셔닝/서사/해설형 인텔리전스**로 패키징하되, 투자조언/자동매매 문구는 금지한다.
- `신시장지표`는 관측/경보형 서비스로 제한하고, 예측 단정·성과 보증이나 수익 약속을 암시하는 문구는 금지한다.

## 3) 통합 사업 포트폴리오 (요청 반영)

### 3.1 축 A — 압축·토큰절감 사업 (최우선)

- 고객: LLM 비용이 큰 B2B(컨택센터, SaaS, 리서치팀, AI 자동화팀).
- 제품: 토큰 절감 API + 비용 리포트 + 품질·복원 투명성 보고서.
- 핵심 가치: 비용 절감, 지연 안정화, 산출물 재현성.
- 금지: “무조건 100% 복원” 같은 과장 주장.

### 3.2 축 B — 초고난도 비정형 텍스트 기반 사업 (고급 해설형)

- 고객: 프리미엄 콘텐츠 구독층, 리서치 독자층, 교육·인문 IP 수요층.
- 제품: `Risk Narrative Brief`(거시 국면 해설형) + 지표 해설 리포트.
- 기술 프레임: 종교 주장이나 형이상학 서사가 아니라, **고난도 비정형 텍스트를 계량 가능한 구조로 변환하는 스트레스 테스트 엔진**으로 설명한다.
- 역할: 직접 시그널 판매가 아닌 리스크 해설·시나리오 보조.
- 금지: 결정론 예언·확정형 투자 문구.

### 3.3 축 C — 명리학 사업 (개인화 인사이트형)

- 고객: 개인 프리미엄 구독, 코치/상담형 파트너, B2B 웰니스 콘텐츠 채널.
- 제품: 개인·그룹용 리스크 성향 인사이트 패키지(비의료/비투자조언).
- 역할: 행동 가이드/리스크 태도 조정 보조.
- 금지: 의료 효능 단정, 실전 자동매매 연결.

### 3.4 축 D — 사상의학 사업 (의료 격벽형)

- 고객: 연구·교육·콘텐츠 파트너(의료행위 아님).
- 제품: 체질 기반 설명형 콘텐츠/리포트/연구 패킷.
- 역할: 의료 서비스가 아닌 비의료 인사이트 IP.
- 금지: 진단/치료/처방으로 오해되는 운영.

### 3.5 축 E — 신시장지표 사업 (관측형 경보 서비스)

- 고객: 리스크팀, 운용지원팀, 리서치 조직.
- 제품: 월간/주간 `regime pressure` 관측 지표 + 이벤트 경보.
- 역할: 매수/매도가 아니라 위험도·노출관리 보조.
- 금지: 성과 보증·확정 예측·실행 지시.

### 3.6 축 F — Topology Radar / Resonance Scanner (B2C 쇼룸)

- 고객: B2C 대중 사용자, 퀀트/리서치 커뮤니티, 잠재 B2B 리드.
- 제품: 자유 대화형 챗봇이 아닌 **비정형 텍스트 위상 레이더** 체험형 쇼룸.
- 입력: 뉴스/공시/발표문 원문 텍스트를 그대로 주입.
- 처리/표현:
  - 15K 아톰 분해 시각화(텍스트 -> 아톰 입자).
  - 4D 텐서 투영(`S/L/K/M`) 편향도 및 균형 이탈량.
  - 역사/구조 공명 점수(예: capitulation resonance %).
- 출력: 서술형 예언이 아니라 **정량 지표 + 재현 가능한 근거 아티팩트 링크**.
- 역할: 리스크 경보 문해력 체험 + 엔터프라이즈 API 세일즈 리드 생성.
- 금지:
  - "내일 오를까/내릴까" 류 결정론 답변.
  - 매수·매도 실행 지시, 성과 보증 표현, 자동 매매 유도 카피.
- 도메인 권고:
  - 공개 쇼룸 1순위: `jemaai.cloud` (공개 전광판/쇼룸 SSOT와 정합).
  - 엔터프라이즈 API CTA 2순위: `a-codeai.com` (`/v1` 분리형 B2B 엔드포인트 문맥).
  - 브랜드 허브/설명 페이지는 `jema-ai.com`에서 연결하되, 실시간성/쇼룸 UI는 `jemaai.cloud`로 집중.
  - `a-codeai.com` 배포는 **정적 랜딩(`/`)과 API(`/v1`, `/health`)를 nginx에서 분리**한다. 운영 예시는 `scripts/deploy/nginx/a-codeai.com.static-plus-compression-api.conf.example`를 기준으로 한다.
  - **허브→쇼룸 CTA 문구(초안)·분기 SSOT:** `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` §1.1b — `jema-ai.com` Next 공개 카피 원천은 `projects/no1kmedi/marketing-site/public-copy.json` (`hub_links`: `showroom_jemaai`, `premium_mkmlife`, `b2b_acodeai`).

### 3.7 MKM AI — 고신뢰 R&D 검증·가속 인프라 (Value Proposition 전환, 2026-05)

**목적:** MKM AI(4AI core + Absolute Balance Coordinator Mode)의 대외·대고객 가치 제안을 **“난제 증명”이나 단정적 초능력 서사에서 분리**하고, 레포에서 실제로 운영 가능한 **Fact-Lock·아티팩트 기반 검증 파이프라인**으로 고정한다.

#### (1) 금지 서술 (Brand / Legal alignment)

Track C 대외 문구·제안서·랜딩에서 다음은 **사용하지 않는다**.

- 밀레니엄 난제·수학 난제를 **“해결했다/증명했다”**는 취지의 단정.
- **“100% 무손실”**, **“무조건 복원”**, **“지연 0”** 등 측정 없는 절대값 보장.
- NotebookLM·브리핑만으로 한 **구현 완료·성능 단정** (`docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 호출 가능 스크립트·exit code가 없는 주장).

대신 기본 프레임은 **§9 External Messaging** 및 본 절의 “검증 인프라” 문장을 사용한다.

#### (2) 전환 후 핵심 가치 제안 (What we sell)

MKM AI가 제공하는 것은 **정답 생성기**가 아니라, 엔터프라이즈·연구 조직의 **R&D 비용(시간·인력·재현 실패 비용)을 줄이는 검증·가속 레이어**다. 운영적으로는 다음 계층을 **자동화·계측·동결**한다.

| 계층 | 역할 (비수학 단정) | 고객 효용 |
|------|-------------------|-----------|
| **Stage A — 빠른 반례·탈락** | 후보 가설·설정을 넓게 스캔하고 취약 케이스를 조기에 제거 | 무의미한 방향으로 가는 실험 비용 절감 |
| **Stage B — 파라미터 스윕** | 상수·정밀도(`mp_dps` 등)·샘플 구간을 체계적으로 탐색 | “그럴듯한 한 번”이 아니라 재현 가능한 조건 집합 확보 |
| **Stage C — 교차검증** | 독립 경로·설정으로 결과를 대조, 편향·구현 버그 검출 | 신뢰할 수 있는 최종 후보와 한계 명시 |
| **Freeze / Handoff** | 수치 로그·JSONL·요약 JSON 등 **동결 아티팩트**로 패키징 후 인간 전문가에게 인계 | 감사·재현·외부 검증 가능한 납품 형태 |

**고객에게 주는 약속의 형태:** “우리가 정답을 증명한다”가 아니라, **“실패를 빨리 찾고, 살아남은 가설만 근거와 함께 넘긴다”**이다.

#### (3) P1(압축·토큰 절감 API)과의 시너지 (Synergy)

`§3.1 축 A` 및 **P1 우선순위**와 직접 맞닿는다.

- **토큰 이코노미:** 압축·토큰 절감은 결국 **입력 길이·호출 패턴·복원 품질 요구**가 바뀔 때마다 재검증이 필요하다. MKM AI 검증 인프라는 **프로파일별·고객별 파라미터 스윕과 교차검증**을 통해 “비용은 줄이되 신뢰 KPI를 깨지 않는 운영점”을 찾는 데 쓴다.
- **지연 안정화:** 동일 부하에서 설정 drift가 나지 않도록 Stage B/C에서 **재현 로그·임계치**를 남기고, Track C **Trust KPI**(재현 가능한 아티팩트·월간 투명성)와 같은 언어로 보고한다.
- **대외 주장의 일관성:** 압축 제품에서 금지하는 **무손실 단정**과 동일하게, MKM AI 스토리도 **측정된 KPI·게이트·아티팩트** 안에서만 확장한다 (`P0_COMMERCIALIZATION_TRACKER.md`의 Fact-Lock·LLM 검증 티어와 동일 선상).

#### (4) 거버넌스 고정 (MKM 내부)

- 연구·탐색 산출물(B-track)과 상용 패키징(Track C)은 **합선하지 않는다** (`§1 Fact-Locked Baseline`).
- **난제·증명 작업**에서 자동 생성되는 lemma 의존 그래프·소요 시간 산출 등 **환각 리스크가 높은 자동 서술**은 Track C 제품 서사에 넣지 않는다. 필요 시 **인간 수학자·Lean 전문가 검토 후**만 별도 연구 자료로 다룬다.

#### (5) 세일즈·제안서에 넣을 한 단락 (복붙용)

`MKM AI는 난제의 증명을 주장하지 않습니다. 다만 대규모 가설과 설정을 빠르게 검증하고, 반례 탐색·파라미터 스윕·교차검증을 통해 재현 가능한 로그와 동결 아티팩트로 정리합니다. 이는 엔터프라이즈 LLM 운영에서 토큰 비용과 지연을 줄이되, 신뢰 KPI와 감사 가능성을 유지하려는 조직에 맞춘 R&D 검증 인프라입니다.`

### 3.8 B2B 우선 상용화 · 기업용 매크로 조기 경보 구독 (2026-05)

**목적:** 대외 **현금 창출 1차 파도**를 **기업·기관 대상 구독형 인사이트**(리포트·대시보드·경보 알림)로 고정한다. `Track A`(실시간 실행·실키 인접)와 **합선하지 않는다** — 내부 운용 엔진은 노출하지 않고, **B-Track에서 파생된 시나리오·관측 인텔**만 포장한다.

| 차원 | 정의 |
|------|------|
| **판매물** | 거시·레짐·리스크 시나리오 및 **분기·월간 브리프**(PDF / 대시보드 접근 / 이메일). 멀티렌즈·관측 지표는 **해설·경보·포지션 보조** 프레임. 투자 자문·매매 지시 아님; 결과에 대한 약속 없음(`§9`). |
| **타겟** | CEO·전략·리스크·운용 지원 등 **B2B 의사결정자**. 개인 리딩방·고객 실키 위탁·거래소 대행 아님. |
| **수익 모델** | 연·월 **구독**, 리포트 주기(주·월·분기), 필요 시 API **읽기 전용** 경보(기존 Macro Risk API 계약 경로와 정합). |
| **운영 경계** | 고객의 거래소 API·실키를 **당사가 저장·중계하지 않음**. 고객 입력은 시나리오·관심 자산군 등 **비실행 파라미터**로 제한. 산출은 **재현 가능한 아티팩트·로그** 중심. |
| **내부 자산** | 실매매·자동 실행 **`A-Track`은 내부 전용 금고**; 대외에는 동 엔진에서 나온 **요약·분석 레일만** 선택적으로 패키징. |

**첫 MVP(상품 뼈대):** **`2026년 하반기 매크로 리스크 경보 리포트`** — (1) 목차 동결 (2) Executive Summary 1p (3) 근거로 삼을 **레포 산출물·스크립트 경로 목록**을 §9와 같은 톤으로 고정한 뒤, 내용은 아티팩트로 채운다. NotebookLM·단발 LLM 출력만으로 최종본 확정 금지(Fact-Lock). **동결 뼈대:** `docs/final/artifacts/track_c_2026_h2_macro_risk_alert_report_mvp_v1.md`.

**법무:** §1·§8·§9 면책·비자문 원칙 전제. 구체 표현·관할은 **법무 검토 후** 대외 사용.

**기술 축 P1~P6과의 관계:** 아래 **§4 매트릭스**는 제품·기술 우선순위이며, 본 절은 **GTM(판매 파도)** 우선순위다. 예: **압축·토큰 API(P1)** 가 기술 상 1순위여도, 대외 **첫 유료 패키지**는 본 B2B 리포트·경보 묶음으로 가져갈 수 있다 — **역할 혼동 금지**.

---

## 4) 우선순위 매트릭스 (2026-04)

**대외 매출 파도(권장, §3.8):** 기업용 **매크로 조기 경보 구독**을 Track C의 **1차 상용 패키징**으로 두고, 기술 축(P1~P6)과 병행하여 영업·납기 계획을 잡는다.

1. **P1 — 압축·토큰절감**
   - 이유: 90일 내 매출화 가능성이 가장 높고 Track C 비자문 구조와 정합성이 가장 높다.
2. **P2 — 신시장지표(관측형)**
   - 이유: 기업 수요가 높고 Track C의 경보형 패키지로 전개 가능하다.
3. **P3 — Topology Radar/Resonance Scanner(B2C 쇼룸)**
   - 이유: 대중 체험 전환율과 차별화가 높고, 비자문·비결정론 구조로 법무 리스크를 상대적으로 낮출 수 있다.
4. **P4 — 명리학(해설형 패키지)**
   - 이유: 콘텐츠/구독형 전개가 가능하나 법적·표현 리스크 관리를 강하게 요구한다.
5. **P5 — 초고난도 비정형 텍스트 기반(해설형 패키지)**
   - 이유: 차별화 포인트는 크지만 상업화는 해설형/리서치형으로 제한하고, B2B에서는 스트레스 테스트 베드 내러티브만 사용해야 안전하다.
6. **P6 — 사상의학(비의료 IP)**
   - 이유: 잠재력은 크지만 규제·오해 리스크가 커서 초기 Track C에서는 제한 운용이 적합하다.

## 5) Packaging Strategy (하나로 묶고, 필요 시 분할)

### 5.1 기본안: One Master Plan + 6 Annex

- 본문 1개: Track C 마스터 전략(이 문서).
- 부속 6개(필요 시 후속 분리):
  - Annex A: 압축·토큰절감 GTM
  - Annex B: 신시장지표 경보 GTM
  - Annex C: Topology Radar/Resonance Scanner B2C 쇼룸
  - Annex D: 명리학 인사이트 상품
  - Annex E: 초고난도 비정형 텍스트 해설형 리포트 상품
  - Annex F: 사상의학 비의료 IP 상품

### 5.2 분할 트리거

- 외부 제출용으로 30페이지를 초과하거나,
- 법무/규제 검토가 사업축별로 달라질 때,
- 세일즈 조직이 산업군별 플레이북을 따로 요구할 때.

## 6) 30-60-90 Execution (우선순위 반영)

### Day 0-30 (P1 론칭)

- 압축·토큰절감 오퍼 1페이지와 가격표 완성.
- Track C 공통 디스클레이머를 랜딩/제안서/API 문서에 고정 삽입.
- 첫 20개 리드 리스트 확정(기존 네트워크 + 인바운드).

### Day 31-60 (P2 병행)

- 신시장지표 관측형 리포트 베타 론칭(주간 1회, 월간 1회).
- 디자인 파트너 3~5곳 인터뷰 및 KPI 부록 고정.
- 압축 API 파일럿 1~2건 유료 전환.

### Day 61-90 (P3 착수)

- Topology Radar/Resonance Scanner 공개 베타 출시(입력 제한 + 허용 필드 고정).
- 엔터프라이즈 API CTA를 `a-codeai.com`으로 연결한 리드 퍼널 A/B 테스트.
- 파일럿 종료 사용자/법인 리드를 Track C 연간 계약 파이프라인으로 전환.

## 7) KPI Contract (사업축 공통)

- Lead KPI: 월 유효 리드 수, 파일럿 전환율, 파일럿→연간 전환율.
- Product KPI: 리포트 정시 납기율, 이벤트 경보 적시성, 고객 재구독률.
- Trust KPI: 재현 가능한 아티팩트 링크/해시/로그, 월간 투명성 리포트 발행율.
- Risk KPI: 법무 문구 위반 0건, 과장 카피 제로, 비자문 원칙 위반 0건.

## 8) Legal/Brand Guardrails (Hard Requirements)

- 투자자문·매매지시·수익보장 암시 문구 금지.
- Track C 산출물에서 직접 주문 시그널/자동실행 힌트 금지.
- 성경/명리/사상 소재는 해설·리스크 인사이트 문맥으로만 사용하며, 대외 메시지는 반드시 "스트레스 테스트 베드" 프레임으로 한정한다.
- 의료·치료·처방으로 오해될 표현 금지.

## 9) External Messaging (fixed)

Default public paragraph:

`MKM provides a governance-driven risk warning and scenario posture service that integrates multi-lens analytics. The service supports exposure-control decisions with reproducible artifacts and verification logs. It is not investment advice, does not provide buy/sell instructions, and does not guarantee returns.`

Enterprise API framing sentence (add-on):

`The engine has been stress-tested on high-complexity, high-ambiguity historical text corpora to validate context filtering and noise suppression under extreme semantic load; production claims remain bounded to measured risk and reliability metrics.`

Neuro-inspired framing policy (communication-only):

`Neuroscience-inspired principles (framing, attention steering, cognitive load reduction) are used strictly as communication design guidance. They are not presented as scientific proof of product outcomes, and all external claims remain artifact-backed, bounded, and framed without implying assured outcomes.`

Short copy:

- Risk Warning First, Not Trade Advice.
- Token Efficiency + Risk Posture, with Reproducible Evidence.
- Governance-driven, Artifact-backed, Operator-in-the-loop.

## 9A) Core Theory Protection (Commercial Security Gate, 2026-05)

**원칙:** Track C는 고객에게 "원시 이론/내부 파라미터"를 판매하지 않는다.  
판매물은 **의사결정 보조 산출물(점수/사분면/경보/해설)**이며, 핵심이론은 `core-engine` 내부에서만 실행한다.

### 9A.1 공개/비공개 경계 (Hard Boundary)

| 구분 | 외부 제공 | 외부 비공개(금고) |
|------|-----------|-------------------|
| 계산 로직 | 최종 상태값·요약 라벨 | X/Y 산식 상세, 내부 가중치, 튜닝 규칙, 중간 피처 기여도 |
| 모델 운영 | 응답 스키마, 상태코드, 감사용 최소 근거 | 룰트리·threshold 실값·실험 히스토리·승격 실험 파라미터 |
| 문서/영업 | 리스크 내비게이션/비자문 문구 | 내부 시그널·스코어 생성 논리, 사내 운용 디테일 |

### 9A.2 제품 아키텍처 (Model-as-a-Service)

1. `core-engine`(비공개): 내부망/VPC에서만 실행, 외부 직접 접근 금지.
2. `presentation-api`(공개): 결과값·요약 상태만 반환, 중간 계산값 미노출.
3. `client dashboard`: 시각화·리포트 전용, 브라우저 번들에 계산식 포함 금지.

### 9A.3 기술·운영 통제

- **필수:** tenant별 API key, rate limit, IP allowlist(enterprise), RBAC.
- **응답 최소화:** "왜 이 점수인가"는 설명 가능한 범위로만 제공하고, 파라미터/룰 ID 원문은 숨김.
- **추적성:** 고객별 워터마킹(리포트/내보내기 식별자) + append-only 접근 로그.
- **비밀관리:** 키/자격증명은 secret manager 또는 로컬 비밀 저장소만 사용, 저장소 커밋 금지.
- **탐지:** 비정상 호출 패턴(대량 추출·역공학 시도) 경보를 운영 KPI에 포함.

### 9A.4 계약·법무 가드 (B2B 기본조항)

- 역공학 금지, 재배포 금지, 파생모델 학습 금지.
- 내부 의사결정 보조 목적 한정(자동매매/자문 대체 금지).
- 산출물 책임 한계, 손실·성과 비보장, 최종 의사결정은 고객 운영자 책임.

### 9A.5 상용화 90일 보안 실행(Track C 연동)

- **Day 0-30:** 공개 API 스키마 민감필드 제거, core/presentation 분리 배포, 감사로그 최소계약 고정.
- **Day 31-60:** tenant 분리·권한모델·워터마크 적용, 엔터프라이즈 키 발급/폐기 runbook 고정.
- **Day 61-90:** 유출대응 드릴(키회전/클라이언트 차단/법무 통지) 월 1회, 역공학 탐지 리포트 정례화.

**Track C 판매 문구 고정(보안 버전):**  
`We commercialize decision-support outputs, not proprietary core formulas. The engine remains server-side and access-controlled; clients receive reproducible risk posture artifacts under a non-reverse-engineering license.`

## 10) Immediate Next Actions

1. **§3.8 MVP:** `2026 H2 매크로 리스크 경보 리포트` — **목차·Executive Summary 1p·근거 아티팩트 경로 표**는 `docs/final/artifacts/track_c_2026_h2_macro_risk_alert_report_mvp_v1.md`에 동결; 본문 수치는 해당 경로의 JSON·로그로 채운다.
2. **B2B 오퍼:** 구독 범위(주기·대시보드·이메일)·면책·신뢰 KPI를 넣은 **1페이지 세일즈 시트** 초안을 Track C 공통 문구(§9)와 함께 고정한다. **자동 생성 초안:** `docs/final/artifacts/track_c_b2b_macro_alert_offer_onepager_latest.md` (`py scripts/build_track_c_macro_risk_mvp_filled_v1.py` 실행 시 MVP와 함께 갱신).
3. 이 문서를 기준으로 `P1(압축)` 세일즈 원페이지와 파일럿 제안서 버전을 동결한다.
4. `P2(신시장지표)` 관측형 주간 리포트 템플릿을 추가하고, 경보 KPI를 명시한다(B2B 브리프와 중복 시 하나의 납기 템플릿으로 통합 검토).
5. `P4/P5/P6(명리/초고난도 비정형 텍스트/사상의학)`은 비자문·비의료·비결정론 고정 문구를 포함한 실험형 패키지로만 운영한다.
6. Topology Radar 쇼룸은 **JSON 계약(허용 필드/금지 필드) -> 와이어프레임 -> 카피라이팅** 순서로 고정해 환각·컴플라이언스 리스크를 선제 차단한다.
7. `§9A` 보안 게이트에 따라 API/대시보드 응답에서 내부 산식·가중치·중간 피처를 제거하고, 계약서(NDA+역공학 금지)와 기술 설정(키·워터마크·감사로그)을 동시 적용한다.

## 11) MKM AI Sales Kit Reference (External-Ready)

- 세일즈킷 루트: `docs/final/artifacts/mkm_ai_sales_kit_v1`
- 숫자/문구 가드(대외 고정): `docs/final/artifacts/mkm_ai_sales_kit_v1/MKM_AI_FACTSAFE_NUMBERS_V1.md`
- API 브랜딩 브리지(계약 비파괴): `docs/final/artifacts/mkm_ai_sales_kit_v1/MKM_AI_API_BRANDING_BRIDGE_V1.md`
- 랜딩 카피 초안: `docs/final/artifacts/mkm_ai_sales_kit_v1/MKM_AI_LANDING_COPY_V1.md`
- 쇼룸 와이어프레임 초안: `docs/final/artifacts/mkm_ai_sales_kit_v1/MKM_AI_SHOWROOM_WIREFRAME_V1.md`
- 세일즈킷 구조 레지스트리: `docs/final/artifacts/mkm_ai_sales_kit_v1/MKM_AI_SALES_KIT_STRUCTURE_V1.json`

### 11.1 계약 SSOT 고정 (중복 스키마 난립 방지)

- Canonical API 계약은 기존 경로를 유지한다:
  - `docs/final/openapi_macro_risk_warning_api_v1.yaml`
  - `docs/final/artifacts/macro_risk_warning_api_response_contract_v1.json`
- `mkm-ai-insight.v1` 같은 신규 스키마 명칭은 OpenAPI/계약/테스트/P0 게이트 반영이 완료되기 전까지 대외 확정명으로 사용하지 않는다.

