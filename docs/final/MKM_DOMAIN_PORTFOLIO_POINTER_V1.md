# MKM 도메인 포트폴리오 포인터 v1 (레포 SSOT 우선)

**목적:** 다수 도메인을 **한 표**로 보되, 사업 서술은 **레포에 고정된 경로**만 진실(SSOT)로 둔다. NotebookLM·구 기획 노트와 **불일치하면 레포·`pm2 describe`를 우선**한다.

**NotebookLM 동기화:** 본 파일을 지휘부 노트북에 **소스로 추가**하면 질의 시 “어느 문서가 기준인지”를 맞추기 쉽다. 교차 노트북 답변은 **상충 가능** — 판정은 아래 **SSOT 열**이다.

---

## 1) 도메인 × 역할 × 문서 × VPS (혼선 방지)

| 도메인 | 제품·역할 (레포 기준 요약) | SSOT / 진입 문서 | VPS·배포 — 혼동 금지 |
|--------|---------------------------|-------------------|----------------------|
| **no1kmedi.com** | **한의사 포털 apex** + **`clinic.`** 서브도메인(Next `/clinician`) · **`research.`** 연구소 정적 · Express **`api.`** | `MKM_DOMAIN_CLINICAL_LANE_V1.md` · `NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` | PM2 `no1kmedi-com` `:3010` · nginx `apply_*_no1kmedi_*_v1.sh` · **jema12 런북 혼용 금지** |
| **mkmlife.com** | mkmlife.com 소비자 제품; **원퀘스천·단건 과금** 락은 동 SSOT §11. 소스는 서브모듈 `projects/mkm/mkm-life`. | 위 SSOT §10·§11, `MKMLIFE_VPS_SSH_CURSOR_CLEANUP_RUNBOOK.md` | PM2 이름 **`mkmlife`** — **`exec cwd`만 본선 Git**. E: 백업 전용(§2.1b). |
| **jema12.com** | **레거시 브랜드 도메인** — 정책: 전 경로 **301 → `https://jema-ai.com`** (path·query 유지). CF Registrar 이전 완료; **zone이 API 토큰에 보이면** `scripts/Invoke-CloudflareJema12RedirectSetup_v1.ps1`. | `SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md`(nginx·studio/broadcast **레거시**), `jema12_cloudflare_zone_v1.json` | **no1kmedi/mkmlife 배포와 분리**. 공개 브랜드·B2B 허브는 **jema-ai.com**만. |
| **jemaai.cloud** | 공개 쇼룸·Public Event Gateway·**실매매와 격리**된 관측 UI. **MKM 패밀리 허브 푸터**(`showroom-hub-footer`) on 정적 보드. | `JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md` · `artifacts/mkm_domain_design_tokens_v1.json` · `run_jemaai_cloud_completion_chain.ps1` = 로컬 점검 · 라이브 푸터: `Run-JemaaiShowroomHubFooterLiveSmoke_v1.ps1` | 게이트웨이·nginx: `jemaai-cloud-mvp`. VPS sync: `sync_showroom_to_vps.ps1`. **api.jemaai.cloud** — `jema12.cloud` 혼용 금지. |
| **a-codeai.com** | L2·압축 API·B2B 대외면: **정적 랜딩과 API 포트 분리** (nginx). | `P0_COMMERCIALIZATION_TRACKER.md`(a-codeai nginx 체크리스트), `scripts/deploy/nginx/a-codeai.com.static-plus-compression-api.conf.example` | **apex가 스텁 JSON만 받아 404 나는 설정** 금지 — `/` vs `/v1/` 분리 우선. |
| **mkmlab.space** | **퇴역 예정** — **301 → `research.no1kmedi.com`** (등록 만료 ~2026-06-20). 콘텐츠 SSOT는 `mkmlab-redesign/` → `/var/www/mkmlab`. | `MKM_DOMAIN_CLINICAL_LANE_V1.md` · `apply_mkmlab_space_retire_301_v1.sh` | 갱신 중단 전 **research** vhost·DNS ensure · `Invoke-No1kmediDomainParallelMigrate_v1.ps1` |
| **research.no1kmedi.com** | **분자한의학 연구소·생산 제품** (구 mkmlab.space). | 동 상위 · `reports/mkmlab_space_readiness_latest.json` | VPS static · CF zone **no1kmedi.com** |
| **jema-ai.com** | **공개 브랜드·Next `metadataBase`**. B2B **`/enterprise`** · 한의사 보조 **`/clinician`**(채팅+CDSS·환자 번들). 소스 `projects/no1kmedi`. | `JEMA_AI_DOMAIN_POINTER_V1.md` · CF DNS ensure 산출: `reports/cloudflare_dns_ensure_jema-ai_com.json`(요약 체인: `reports/cloudflare_dns_ensure_chain_latest.json`) | **실측(2026-05-16):** upstream `127.0.0.1:3010` · PM2 `no1kmedi-com` **`cwd=/opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi`**. 배포: `Deploy-No1kmediDestinyTarball_v1.ps1` (`-RunApiSmoke` 권장). VPS `.env.local`: `MKM_WORKSPACE_ROOT`·`MKM_PYTHON`·`KM_CLINICIAN_PRO_EMAIL_ALLOWLIST`. |
| **logos.jema-ai.com** | **성경·텍스트 연구 워크스페이스** (Track B 상용 표면) — GraphRAG·citation lock·기관 파일럿. **교리 판매·Track A·실매매 격리.** | `docs/final/artifacts/logos_research_commercial_product_v1_latest.json` · `projects/no1kmedi/src/app/logos-research/page.tsx` · 메트릭 `reports/logos_research_product_metrics_v1_latest.json` | **farm.jema-ai.com** 과 동일: Next middleware rewrite `/` → `/logos-research` · apex `jema-ai.com/logos-research` → **308** canonical 서브도메인. DNS: jema-ai.com zone CNAME `logos` → 동일 origin. |
| **personadiary.com** | B2C **찰나의 나라** — 뉴스·날씨·거시×지금의 나 융합 일상 동반 · moment 질문·리추얼·일기(HYPO) · `no1kmedi` `/personadiary`. **데이터·결제 미확정**. | `PERSONADIARY_DOMAIN_POINTER_V1.md` · `artifacts/personadiary_b2c_business_plan_v1_latest.md` · `personadiary_preview_ops_v1_latest.json` | **본선 연결 전** DB·결제 **합선 금지**. mkmlife API/DB 공유 가정 금지. |

**Cloudflare — 레포 앵커 (최소):** `scripts/data/hostinger_full_exit/`에 **`schema: *_cloudflare_zone_v1` JSON**이 있는 apex는 **no1kmedi.com, mkmlife.com, mkmlab.space, a-codeai.com, jema12.com, personadiary.com** (파일명 접두와 동일). **`jema-ai.com`·`jemaai.cloud`는 이 폴더에 별도 zone 픽스처 파일이 없음** — DNS 레코드 ensure·점검 산출은 위 표 행의 `reports/cloudflare_dns_ensure_*.json` 및 `reports/cloudflare_dns_ensure_chain_latest.json`을 우선한다. 토큰·Redirect·메일 라우팅 등 절차는 `docs/final/JEMA12_PUBLIC_DOMAIN_AND_DEPLOY_HANDOFF_2026-04-07.md`, `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`(Cloudflare/Email Routing 표행)와 `scripts/Invoke-Cloudflare*.ps1` 포인터를 병행한다.

### 1.1 쇼룸·체험 표면 배치 (도메인 × 디자인 의도, 2026-05-05)

Track C·공개 쇼룸 논의와 동일 선상: **실매매·조종실은 어디에도 공개 URL로 붙이지 않는다.** 아래는 **어느 도메인에 어떤 “보이는 증거”를 둘지** 고정한다. 구현·경로 판정은 여전히 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·스크립트.

| 표면(무엇을 보여주나) | 도메인(호스트) | 디자인·톤 | 금지·경계 | SSOT |
|----------------------|----------------|----------|----------|------|
| **공개 전광판** — 지연·추상 시그널, Topology/BTC·매크로 **관측** 데모, `public-event.v1` 기반 쇼룸 HTML | **jemaai.cloud** | 다크·미니멀 **보드** + **MKM 패밀리 허브 푸터**(jema-ai·mkmlife·research 링크); 티커·가상 반응은 **ID 매핑**만 | 주문·체결·실키·정확 포지션 **공개 금지** | `JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md`, `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`, `mkm_domain_design_tokens_v1.json` |
| **개인화 라이프 허브** — 검색·오늘 맞춤 관측 덱(L0)·가벼운 맥락 답변(L1) + **원퀘스천** 유료 심화 리포트(L2); 광고 없음·뉴스 **포털 아님**(관측 덱·`PUBLIC_FACING` v1.6) | **mkmlife.com** | **포털형 홈**(중앙 검색 + HP 카드 + 덱 프리뷰) + 리포트 카드 완결; 무한 채팅·챗뷔페 기본값 아님; 배지·면책 고정 | 실거래 퍼널·원격 진료·언론사형 **뉴스 포털** 서술과 **합선 금지** | `NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` §10–§11 · 홈 `HomeLifePortal` |
| **브랜드·허브·진입** — 회사 소개, 깊은 링크, 문서 하단 디스클레이머 | **jema-ai.com** | 라이트 마케팅 랜딩; **CTA는 mkmlife/jemaai로 분기** | 쇼룸 **실시간 전광판 UI**는 기본 **여기에 두지 않음**(혼잡·이중 유지보수 방지) | `JEMA_AI_DOMAIN_POINTER_V1.md` |
| **B2B 압축·API 대외면** | **a-codeai.com** (및 정책에 따른 API 호스트) | 정적 랜딩 vs `/v1` API **경로 분리** | apex 스텁만 노출 404 류 | `P0_COMMERCIALIZATION_TRACKER.md`·nginx 예시 |
| **분자한의학 연구소·생산 제품** | **research.no1kmedi.com** (구 mkmlab.space) | 연구·제조 스토리; **상업·B2B는 jema-ai.com** | AI 쇼룸·실매매 **합선 금지** | `mkmlab-redesign/` · `TRACK_C` §3.0 |
| **성경·텍스트 연구 워크스페이스** | **logos.jema-ai.com** | 학술·연구 톤; Fact-Lock 메트릭 스냅샷 | 교리 판매·투자·Track A **금지** | `logos_research_commercial_product_v1_latest.json` |
| **한의사 진료 보조** | **clinic.no1kmedi.com** · **no1kmedi.com** apex | SOAP·CDSS·/clinician; **공식 URL은 app.jema-ai.com** | consumer·MAI **합선 금지** | `MKM_DOMAIN_CLINICAL_LANE_V1.md` |
| **백엔드 API·PayApp** | **api.no1kmedi.com** | Express·결제 — **UI 없음** | apex 포털 nginx와 **vhost 분리** | `NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` §1 |
| **찰나의 나라 일상 동반** | **personadiary.com** | 따뜻·귀여움 · 뉴스·날씨·거시×지금의 나 **융합 카드** · moment 질문·리추얼 | 뉴스 포털·운세·투자·mkmlife 결제 **합선 금지** | `personadiary_b2c_business_plan_v1_latest.md` |

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
| **jema-ai.com** | **research.no1kmedi.com** | 「MKM LAB 분자한의학 연구소·생산 제품」 | 연구소·R&D; **AI·압축 수치 합선 금지** (`TRACK_C` §3.0). |
| **research.no1kmedi.com** | **jema-ai.com** | 「도입·파트너·B2B·클리닉 문의」 | 상업·Track C는 **jema-ai**; 연구소는 **소개·제품만**. |
| **jema-ai.com** | **logos.jema-ai.com** | 「성경·텍스트 연구 워크스페이스 (Logos)」·「Scripture Research Workspace」 | GraphRAG·citation lock · **research_only** · 교리·투자·실매매 **아님**. |
| **logos.jema-ai.com** (푸터) | **jema-ai.com** | 「JEMA AI 소개」·「Enterprise」 | 브랜드 허브; 압축 %·MS 헤드라인 **합산 금지**. |
| **jema-ai.com** | **personadiary.com** (`/personadiary`) | 「Persona Diary · 찰나의 나라」 | 일상 동반·리플렉션 **프리뷰**; 운세·투자·mkmlife 결제 **아님** (`personadiary_b2c_business_plan_v1_latest.md`). |
| **jema-ai.com** | **clinic.no1kmedi.com** | 「한의사 포털 (no1kmedi)」 | 현장 북마크; **제안서 URL은 app.jema-ai.com/clinician**. |

`jema-ai.com` 전용 상세·미확정 항목: `JEMA_AI_DOMAIN_POINTER_V1.md` — CTA는 **이 표(1.1b)와 `§1.1` 역할**에 맞출 것.

**구현 원천(코드):** `projects/no1kmedi/marketing-site/public-copy.json` — `research_mkmlab` → **`https://research.no1kmedi.com`** · `research_logos` → **`https://logos.jema-ai.com`** · `clinician_no1kmedi_portal` → **`https://clinic.no1kmedi.com`**. 표(1.1b)와 불일치 시 **먼저 JSON을 고치고** 본 표를 개정한다.

#### 1.1c 공통 엔진 vs 도메인 어댑터 (킬러 아이템 · 혼동 방지, 2026-06-22)

**목적:** 「성경 GraphRAG = logos」「초개인화 = mkmlife」「personadiary = 같은 엔진·다른 배선」을 **한 표**로 고정한다. **모노레포 파이프라인 공유 ≠ 제품·DB·결제·면책 합선.**

**공통 엔진 (B-track · 모노레포 scripts):**

```text
Query → Subgraph router / GraphRAG → Insight (four-slot 등) → Visualization → Feedback (path ledger stub)
```

| 단계 | 대표 SSOT |
|------|-----------|
| Router | `scripts/run_logos_subgraph_graphrag_router_v1.py` |
| 체인 | `scripts/run_question_semantic_rag_bridge_chain_v1.py` |
| 경로 기록 | `scripts/logos_query_path_ledger_v1.py` · `ingest_magic_orb_path_feedback_to_ledger_v1.py` |
| 코퍼스 레인 | 31k manifest · meaning graph(부분 PoC) · concept_bridge — **물리 merge 아님** (`mkm_three_exit_branding_matrix_v1` `shared_backend`) |

**도메인 어댑터 (제품마다 교체):** `corpus_lane` · 킬러 UX · 카피·면책·SKU · `send_gate` / `research_only` 정책.

| 도메인 | 킬러 표면 | 주 목적 | 코퍼스·배선 | 배관(router·path) 노출 |
|--------|-----------|---------|-------------|------------------------|
| **logos.jema-ai.com** | GraphRAG **연구 워크스페이스** | 성경·텍스트 **연구 통찰 생성** · citation lock | concept_bridge · 원어 · 31k lane | **보임** |
| **jemaai.cloud** v6 | 로고스 **관측소** (출구2) | 목회·연구가 · 재현·게이트·XAI | 동일 corpus lane · honest_metrics | **보임** |
| **mkmlife.com** `/oracle-sphere` | **마법구슬** (출구1) | 초개인화 **대중 체험** · 다중렌즈 리포트 | Logos subgraph + **명리 내장**(별도 학술 UI 없음) | **숨김** (consumer) |
| **personadiary.com** | Daily Guide · Ritual/Lattice | **찰나의 나라** · 일상 동반 | `commander_daily_fortune` 등 upstream 빌드 | **숨김** · `preview_only` |

**`jema-ai.com`:** 브랜드 **허브만** — 위 표면으로 **CTA 분기**(§1.1b). 성경 연구 홈·초개인화 홈 **아님**.

**혼동 금지 (에이전트 · 사업계획서 · NL 이관 공통):**

1. **mkmlife Logos 렌즈** ≠ **logos.jema-ai.com** 연구 워크스페이스 (같은 코퍼스 레인을 쓸 수 있으나 **표면·SKU·면책 분리**).
2. **personadiary** ≠ mkmlife **API·DB·결제** — upstream 빌드 공유만 (`PERSONADIARY_DOMAIN_POINTER_V1.md`).
3. **성경 meaning graph** = query-time subgraph + Path Ledger **방향** — 31k 전수 그래프 **미완** (`LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md` GAP).
4. **FAIL-COMP-004:** Universal Root · 압축 KPI · Logos path 점수 **한 헤드라인 합산 금지**.
5. **Y1 Hero** = GitHub `mkm-universal-root` — 위 B2C 킬러와 **별 Plane** (`TRACK_C` §3.0b).

**교차 SSOT:** `docs/final/artifacts/mkm_three_exit_branding_matrix_v1_latest.json` · `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` **§3.0d** · `K_STARTUP_DOMAIN_SERVICE_MAPPING_V1_DRAFT.md` §1.1.

---

## 2) 전역 규칙 (VPS 혼선 방지)

0. **토폴로지:** **Hostinger VPS = 유일 compute** · **Cloudflare = 유일 엣지**(DNS·proxy·메일). SSH `vps-mkmlife` vs `MKM_VPS_HOST` 는 **표기만 다를 수 있음** — `docs/final/MKM_HOSTINGER_CLOUDFLARE_TOPOLOGY_V1.md`.
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

- **임상·체질·MAI 레인:** `docs/final/MKM_DOMAIN_CLINICAL_LANE_V1.md` — physician_gold vs consumer_survey_only · 허브 CTA.
- **jema-ai.com:** `docs/final/JEMA_AI_DOMAIN_POINTER_V1.md` — 확정 전 금지·체크리스트.
- **personadiary.com:** `docs/final/PERSONADIARY_DOMAIN_POINTER_V1.md` — 동일.
