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
| **jema-ai.com** | B2B 한의원 등 기획은 노트 참고. 레포 **포인터만** 확정: 확정 전 타 도메인 런북 금지. | `JEMA_AI_DOMAIN_POINTER_V1.md` | **mkmlife / no1kmedi / jema12 와 동일 VPS라도** 서버블록·PM2 **이름으로 구분**. |
| **personadiary.com** | B2C 일기 등 기획은 노트 참고. 레포 **포인터만** — 데이터·본선 미확정. | `PERSONADIARY_DOMAIN_POINTER_V1.md` | **본선 연결 전** 도메인·repo·PM2 **한 줄 확정** 없이 VPS에 합선하지 말 것. |

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

**개정:** 도메인 추가·PM2 이름 확정 시 표만 갱신한다.

---

## 4) 미확정 도메인 전용 포인터 (상세)

- **jema-ai.com:** `docs/final/JEMA_AI_DOMAIN_POINTER_V1.md` — 확정 전 금지·체크리스트.
- **personadiary.com:** `docs/final/PERSONADIARY_DOMAIN_POINTER_V1.md` — 동일.
