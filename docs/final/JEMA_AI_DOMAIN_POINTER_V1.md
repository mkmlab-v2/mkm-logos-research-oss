# jema-ai.com — 도메인 포인터 v1 (미확정 항목 명시)

**목적:** `jema-ai.com` 을 **jema12.com · no1kmedi.com · mkmlife.com 과 같은 배포 절차로 취급하지 않도록** 레포에 고정한다. NotebookLM·구 기획 문서의 B2B 한의원 등 서술은 **참고**이며, **본선 판정은 아래 확정 필드**다.

---

## 1) 현재 상태 (Fact-Lock)

| 항목 | 값 |
|------|-----|
| **레포 내 전용 앱 경로 (워크스페이스 후보)** | 모노레포 `projects/no1kmedi` (Next.js; `src/app/layout.tsx` 의 `metadataBase` 가 `https://jema-ai.com`). **배포·PM2·nginx 본선 경로는 별도 확정 문서로만 판정**(`NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` 등과 혼동 금지). |
| **전용 런북·배포 스크립트** | **없음** — 별도 문서화 전까지 **타 도메인 런북 복붙 금지**. |
| **PM2 앱 이름 / `exec cwd`** | **미확정** — 확정 후 `pm2 describe` 실측으로만 본선 판정. |
| **VPS 호스트** | no1kmedi/mkmlife/jema12 와 **동일 물리일 수 있음** — 그래도 **nginx `server_name`·upstream·PM2 이름은 분리**. |

---

## 2) 확정 전 금지 (VPS·혼선 방지)

- **jema12** `apply_jema12_nginx_snippet.sh` · **mkmlife** `deploy-to-hostinger.ps1` · **no1kmedi** PM2 절차를 **jema-ai 전용이라고 가정하고 그대로 적용**하지 않는다.
- **한 `server { }` 블록**에 jema-ai 와 다른 브랜드 도메인의 `root`/`proxy_pass` 목적을 **섞지 않는다**.
- 기획 노트만 보고 **실키·결제·의료 컴플라이언스** 경로를 본선에 연결하지 않는다 (`P0` 지휘관 게이트·법무 별도).

---

## 3) 확정 시 이 문서에 채울 항목 (체크리스트)

- [ ] Git 원격 저장소 URL (또는 모노레포 하위 경로)
- [ ] 로컬 작업 디렉터리 (Cursor 기본 열 폴더)
- [ ] PM2 프로세스 이름 · `pm2 describe` 로 확인한 `exec cwd`
- [ ] nginx 설정 파일 경로(본선) 및 `server_name`
- [ ] `MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` 표 갱신

---

## 4) 교차 참조 (혼동 금지)

- `jema-ai.com` ≠ `jema12.com` — `docs/final/JEMA12_PUBLIC_DOMAIN_AND_DEPLOY_HANDOFF_2026-04-07.md` · `SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md` 는 **jema12·jemaai.cloud 축**.
- `jema-ai.com` ≠ `no1kmedi.com` / `mkmlife.com` — 경로 SSOT는 `NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` (다른 제품).

**개정:** 위 체크리스트가 채워지면 본 문서 제목을 `..._v2` 로 올리거나 “확정” 절을 추가한다.
