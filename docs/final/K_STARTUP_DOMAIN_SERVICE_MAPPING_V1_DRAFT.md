# MKM 도메인–서비스 매핑 (대외 제출용 부록 1장) · [DRAFT]

**Status:** `[DRAFT]` — 법무·`ready_for_external_send` 통과 전 대외 send 금지.  
**SSOT:** `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` · `docs/final/artifacts/mkm_three_exit_branding_matrix_v1_latest.json` · `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` **§3.0**(도메인 분리) · §3.1·§3.6·§3.8 · §4  
**Paste copy:** `reports/kstartup_majung_paste_ready/kstartup_domain_service_mapping_v1_draft.md` (동기 유지)

---

## 1. 한 줄 요약

MKM은 **8개 apex 도메인**으로 B2C 체험·공개 쇼룸·B2B API·브랜드 허브·**연구소·제품(mkmlab.space)**·레거시·옵션을 **물리 분리**한다. **연구소 홈 ≠ AI 홈:** `mkmlab.space` / `jema-ai.com` — `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.0. 백엔드는 공유할 수 있으나 **UI·브랜드·실매매·결제·의료 트리거는 합선하지 않는다.**

---

## 2. 보유 apex × 역할 × Track C 축

| 도메인 | 서비스·표면 | 대상 | Track C / GTM | 합선 금지 |
|--------|-------------|------|---------------|-----------|
| **jema-ai.com** | 브랜드 허브 · `app.jema-ai.com/enterprise` B2B · `/clinician` (내부) | 기업·파트너 | §3.8 **1차 유료 파도**(매크로 경보 구독) 영업면 | 쇼룸 UI·실매매·실키 |
| **jemaai.cloud** | 공개 쇼룸 · Logos Oracle v6 · Topology Radar · `public-event.v1` | 대중·리서치·리드 | §3.6 쇼룸 · §3.5 관측 지표 | 주문·체결·실키·확정 예측 |
| **mkmlife.com** | 원퀘스천 · **`/oracle-sphere` 마법구슬 B2C** | 소비자 | §3.3 명리(구슬 내장) · 출구1 DECOY-P0 | 실거래·투자 조언·Track A |
| **a-codeai.com** | **P1 압축·토큰 API** · `/` 정적 · `/v1`·`/health` API (nginx 분리) | B2B·엔터프라이즈 | **§3.1 축 A (기술 1순위)** | B2C UI·쇼룸 임베드 |
| **no1kmedi.com** | Express API · PayApp 축 (레거시 내부 식별) | 인프라 | API 백엔드 | 공개 브랜드명·쇼룸 본거지 아님 |
| **jema12.com** | 레거시 **301 → jema-ai.com** · `/studio` → v6 데모 진입 | 레거시 유입 | 진입 전용 · CF 에지 301 권장 | 제품 본거지 아님 |
| **mkmlab.space** | **MKM LAB 분자한의학 연구소** — 발효 NO 대사체·연구소 생산 제품 소개 | 실물·R&D·건기식(부종목) | **Track C와 별 축** (`TRACK_C` §3.0) | AI·쇼룸·압축 API **본거지 아님** · **VPS+Cloudflare** (`Sync-MkmlabRedesignToVps_v1.ps1`) |
| **personadiary.com** | **preview_only** · 일기 콘셉트 셸 · **데이터·결제 없음** | B2C 옵션 | 2차 옵션 프리뷰 | §3.8 enterprise·mkmlife와 본선 합선 금지 |

**서브호스트(자주 사용):** `app.jema-ai.com` · `api.jemaai.cloud` · `api.no1kmedi.com`

---

## 3. 3출구 (제품 면 · `mkm_three_exit_branding_matrix_v1`)

| 출구 | 브랜드 | 도메인 | 대상 | 상태 |
|------|--------|--------|------|------|
| **1** | 마법구슬 오라클 | **mkmlife.com** `/oracle-sphere` | 대중 · 체험·다중렌즈 리포트(면책) | DECOY D1 done · 결제는 오픈베타 후 |
| **2** | 로고스 관측소 | **jemaai.cloud** v6 (`?product=1`) | 목회·성경 연구 · 아티팩트·NON_GATING | LO-CG Exit done · `[HYPO]`/연구 표면 |
| **3** | 사상 CDSS | 독립 임상판 **[DEFERRED]** · `/clinician` 인접 | 면허 한의사 | MS K3 비전만 · post 5/28 |

**명리 배치:** 별도 학술 UI 없음 — **출구1(mkmlife)에만 내장** (`myeongni_placement`: exit_1_only).

---

## 4. 허브 CTA 분기 (`public-copy.json` · §1.1b)

| 출발 | 목적지 | 용도 |
|------|--------|------|
| jema-ai.com | **jemaai.cloud** / `api.jemaai.cloud` | 공개 관측 보드 · Topology · Logos 데모 |
| jema-ai.com | **mkmlife.com** | 원퀘스천 · 마법구슬 B2C |
| jema-ai.com | **a-codeai.com** | 토큰·압축 API (B2B) |
| jema-ai.com | `/personadiary` (personadiary.com 호스트) | **2차 옵션 프리뷰 셸** — 주력 매출과 문맥 분리 |

---

## 5. 매출·기술 우선순위 (Track C §4 — 역할 혼동 금지)

| 구분 | 우선 | 도메인 |
|------|------|--------|
| **GTM 1차 파도** | B2B 매크로 경보 구독 | jema-ai.com/enterprise + jemaai 데모 |
| **기술 P1** | 압축·토큰 절감 API | **a-codeai.com** |
| **신뢰·리드** | Topology·쇼룸 | jemaai.cloud |
| **B2C 현금흐름(가설)** | 구슬·원퀘스천 | mkmlife.com |

---

## 6. 대외 면책 (제출물 하단 고정)

- 본 표는 **아키텍처·역할 분리** 설명용 `[DRAFT]`이며, **투자·매매·수익·적중·무손실·100%·당선·Track A 승격**을 단정하지 않는다.
- 벤치 수치(예: 압축 ~47%·Jaccard)는 **frozen bench·정책 하한 조건**이며, ms·BOM 절감 입증과 **동일 선언 아님** (RQ-017).
- 성경(Logos)·쇼룸·Wire PoC는 **`[HYPO]`·`[NON_GATING]`·연구·관측** — 실매매·실전 트리거와 **합선 없음**.
- **`ready_for_external_send: false`** — 법무 sign-off 전 최종 대외 send 금지 (`PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` v1.7).

---

## 7. 인프라 권장 (FinOps · 1줄)

`jema12.com/studio` → v6 리다이렉트는 **Cloudflare 에지 301** 우선(원본 VPS 핸드셰이크 최소화). 점검: `scripts/verify_jema12_studio_oracle_redirect_v1.ps1` (`op5_pass`).
