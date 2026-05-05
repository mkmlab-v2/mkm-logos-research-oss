# MKM 도메인 포트폴리오 포인터 v1 (레포 SSOT 우선)

**목적:** 다수 도메인을 **한 표**로 보되, 사업 서술은 **레포에 고정된 경로**만 진실(SSOT)로 둔다. NotebookLM·구 기획 노트와 **불일치하면 레포·`pm2 describe`를 우선**한다.

**NotebookLM 동기화:** 본 파일을 지휘부 노트북에 **소스로 추가**하면 질의 시 “어느 문서가 기준인지”를 맞추기 쉽다. 교차 노트북 답변은 **상충 가능** — 판정은 아래 **SSOT 열**이다.

---

## 1) 도메인 × 역할 × 문서 × VPS (혼선 방지)

| 도메인 | 제품·역할 (레포 기준 요약) | SSOT / 진입 문서 | VPS·배포 — 혼동 금지 |
|--------|---------------------------|-------------------|----------------------|
| **no1kmedi.com** | MKM LAB/가디언·no1kmedi 웹·Express API 쪽 축 (`projects/no1kmedi/`, `payapp-api`). | `NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md`(경로·PM2), `no1kmedi` 실행보고 노트(NotebookLM, 참고) | PM2 `no1kmedi-com` / `no1kmedi-payapp-api` — **jema12 런북과 절차 혼용 금지**. |
| **mkmlife.com** | mkmlife.com 소비자 제품; **원퀘스천·단건 과금** 락은 동 SSOT §11. 소스는 서브모듈 `projects/mkm/mkm-life`. | 위 SSOT §10·§11, `MKMLIFE_VPS_SSH_CURSOR_CLEANUP_RUNBOOK.md` | PM2 이름 **`mkmlife`** — **`exec cwd`만 본선 Git**. E: 백업 전용(§2.1b). |
| **jema12.com** | 브랜드·허브·라우트 이슈 시 **JEMA12 전용 런북**; Next 전체가 레포에 없을 수 있음. | `SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md`, `JEMA12_PUBLIC_DOMAIN_AND_DEPLOY_HANDOFF_2026-04-07.md` | **no1kmedi/mkmlife 배포 절차와 분리**. nginx·스니펫은 jema12 예시만. |
| **jemaai.cloud** | 공개 쇼룸·Public Event Gateway·**실매매와 격리**된 관측 UI. | `JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md`(프로젝트 경로는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 표), `run_jemaai_cloud_completion_chain.ps1` = 로컬 점검, **배포 아님** | 게이트웨이·nginx 예시는 bitcoin-trading `jemaai-cloud-mvp` 경로. **api.jemaai.cloud 권장** — `jema12.cloud`와 동일 가정 금지(핸드오프 표). |
| **a-codeai.com** | L2·압축 API·B2B 대외면: **정적 랜딩과 API 포트 분리** (nginx). | `P0_COMMERCIALIZATION_TRACKER.md`(a-codeai nginx 체크리스트), `scripts/deploy/nginx/a-codeai.com.static-plus-compression-api.conf.example` | **apex가 스텁 JSON만 받아 404 나는 설정** 금지 — `/` vs `/v1/` 분리 우선. |
| **mkmlab.space** | (레포 서술) 회사/랩 **랜딩·R&D 쇼케이스 이전 후보** — `no1kmedi`와 브랜드 분리 논의가 NotebookLM·실행보고에 있음. **단일 배포 SSOT는 호스트 실측 후 확정.** | `NO1KMEDI` SSOT 표(1.1), no1kmedi 실행보고 노트(참고) | no1kmedi 클리닉 전환 시 **랩 콘텐츠 이전** 등 — **한 nginx에 목적 섞지 말 것**. |
| **jema-ai.com** | **공개 브랜드·Next `metadataBase`**. 소스 트리는 `projects/no1kmedi`(폴더명은 레거시; 문서·UI에서는 **jema-ai.com**으로만 호칭). 기획 노트의 B2B 등은 참고. | `JEMA_AI_DOMAIN_POINTER_V1.md` | **mkmlife / no1kmedi.com / jema12 와 동일 VPS라도** 서버블록·PM2 **이름으로 구분**. |
| **personadiary.com** | B2C 일기 등 기획은 노트 참고. 레포 **포인터만** — 데이터·본선 미확정. | `PERSONADIARY_DOMAIN_POINTER_V1.md` | **본선 연결 전** 도메인·repo·PM2 **한 줄 확정** 없이 VPS에 합선하지 말 것. |

### 1.1 쇼룸·체험 표면 배치 (도메인 × 디자인 의도, 2026-05-05)

Track C·공개 쇼룸 논의와 동일 선상: **실매매·조종실은 어디에도 공개 URL로 붙이지 않는다.** 아래는 **어느 도메인에 어떤 “보이는 증거”를 둘지** 고정한다. 구현·경로 판정은 여전히 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·스크립트.

| 표면(무엇을 보여주나) | 도메인(호스트) | 디자인·톤 | 금지·경계 | SSOT |
|----------------------|----------------|----------|----------|------|
| **공개 전광판** — 지연·추상 시그널, Topology/BTC·매크로 **관측** 데모, `public-event.v1` 기반 쇼룸 HTML | **jemaai.cloud** | 다크·미니멀 **보드**; 티커·가상 반응은 **ID 매핑**만; “실시간 무지연” 문구 없이 SPEC상 지연·면책 | 주문·체결·실키·정확 포지션 **공개 금지** | `JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md`, `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` |
| **프리미엄 소비자 제품** — 원퀘스천·단건 리포트(명리·사상·로고스 렌즈 병렬) | **mkmlife.com** | **리포트 카드** 중심·단건 완결; 챗뷔페형 기본값 아님; 배지·면책 고정 | 실거래 퍼널·원격 진료 동선과 **합선 금지** | `NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` §10–§11 |
| **브랜드·허브·진입** — 회사 소개, 깊은 링크, 문서 하단 디스클레이머 | **jema-ai.com** | 라이트 마케팅 랜딩; **CTA는 mkmlife/jemaai로 분기** | 쇼룸 **실시간 전광판 UI**는 기본 **여기에 두지 않음**(혼잡·이중 유지보수 방지) | `JEMA_AI_DOMAIN_POINTER_V1.md` |
| **B2B 압축·API 대외면** | **a-codeai.com** (및 정책에 따른 API 호스트) | 정적 랜딩 vs `/v1` API **경로 분리** | apex 스텁만 노출 404 류 | `P0_COMMERCIALIZATION_TRACKER.md`·nginx 예시 |
| **MKM LAB / API / 가디언** | **no1kmedi.com** | 제품 쇼룸 **메인 무대로 쓰지 않음**(실측 제품이 따로 있으면 예외는 표 개정) | jema12 배포 런북과 혼용 금지 | `NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` §1 |

**와이어·카피 순서(Track C 고정):** JSON 계약(허용/금지 필드) → 와이어프레임 → 카피 (`TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.6·실행 항목 참조). 초안 자산: `docs/final/artifacts/mkm_ai_sales_kit_v1/MKM_AI_SHOWROOM_WIREFRAME_V1.md`(있을 때).

#### 1.1b 진입·CTA (초안, 법적 확정문 아님)

**jema-ai.com** 랜딩·푸터에서 **다른 도메인으로 보내는 기본 분기**다. 문구는 법무·스토어 심사 전 **가이드**이며, `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`·`TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` 면책과 충돌 시 **후자 우선**.

| 출발 | 목적지 | CTA 라벨 (한국어 초안) | 한 줄 각주 |
|------|--------|------------------------|------------|
| jema-ai.com | **jemaai.cloud** | 「공개 관측 보드 보기」·「Topology·매크로 데모」 | 지연·추상 **관측**; 투자 권유·주문·수익 보장 **아님** (`JEMAAI` SPEC). |
| jema-ai.com | **mkmlife.com** | 「원퀘스천 프리미엄 리포트」·「질문 한 개, 다중 렌즈 리포트」 | 제품·면책·퍼널은 **mkmlife** SSOT §10–§11. |
| jema-ai.com | **a-codeai.com** (또는 정책상 API 랜딩) | 「토큰·압축 API (B2B)」 | API·정적 경로 분리; `P0` a-codeai 절. |
| jemaai.cloud (푸터/보조) | **jema-ai.com** | 「JEMA AI 소개」 | 브랜드 허브; 전광판 **중복 임베드**는 기본 금지(이중 유지보수). |
| **mkmlife.com** (필요 시) | jemaai.cloud | 「라이브 데모·공개 보드」(선택) | **소비자 본 퍼널**은 리포트 구매; 쇼룸은 **신뢰·채널** 보조. |

`jema-ai.com` 전용 상세·미확정 항목: `JEMA_AI_DOMAIN_POINTER_V1.md` — CTA는 **이 표(1.1b)와 `§1.1` 역할**에 맞출 것.

**구현 원천(코드):** Next 브랜드 허브 공개 카피는 `projects/no1kmedi/marketing-site/public-copy.json` (`hub_links.showroom_jemaai` 등) — 표(1.1b)와 불일치 시 **먼저 JSON을 고치고** 본 표를 개정한다.

---

## 2) 전역 규칙 (VPS 혼선 방지)

1. **배포 런북은 도메인별로 읽는다.** jema12 절차를 mkmlife Hostinger에 적용하지 않는다.
2. **본선 경로는 `pm2 describe <앱>`의 `exec cwd`.** 문서·기억·NotebookLM 문장이 달라도 **실측 우선**.
3. **G: 공유 볼트 / E: 백업** 은 아티팩트·백업용. **라이브 소스 SSOT 아님** (`MKMLIFE` 런북 §5·§6, `NO1KMEDI` §2.1b).
4. **실매매·올그린·결제 실키** 는 `AGENTS.md`·`P0` 지휘관 게이트 — 도메인 포트폴리오 표가 **자동 GO를 대체하지 않는다.**

---

## 3) NotebookLM 쪽에 둘 것

- **본 파일**(포인터 표) + 이미 있는 **작전지휘부·Fusion Hub·no1kmedi 실행보고** — 질의 시 “레포 SSOT 열”을 인용하라고 프롬프트에 한 줄 넣는다.
- 노트 간 **숫자·포트·도메인 역할이 다르면** → **이 파일과 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`를 우선**한다고 명시.
- 사업 우선순위 질의(무엇을 먼저 팔지)는 **`docs/final/P0_COMMERCIALIZATION_TRACKER.md`의 GTM 업데이트 절**을 우선 참조하고, 도메인 문서는 역할/배포 격벽 판단에만 사용한다.

**개정:** 도메인 추가·PM2 이름·쇼룸 배치 확정 시 §1 및 §1.1 표를 갱신한다.

---

## 4) 미확정 도메인 전용 포인터 (상세)

- **jema-ai.com:** `docs/final/JEMA_AI_DOMAIN_POINTER_V1.md` — 확정 전 금지·체크리스트.
- **personadiary.com:** `docs/final/PERSONADIARY_DOMAIN_POINTER_V1.md` — 동일.
