# no1kmedi / mkmlife 레포 경로 SSOT (2026-04-08)

목적: `mkmlife.com` 관련 작업 시 로컬·VPS 경로 혼동(다른 프로젝트 런북과 섞임)을 막기 위한 단일 기준 문서.

## 1) 범위 분리 (혼동 금지)

- 이 문서는 **no1kmedi / mkmlife 계열**의 로컬 모노레포 경로 + **VPS PM2 실측 잠금값**을 한곳에 묶는다. (`payapp-api`만이 아님.)
- `jema12.com`, `jemaai.cloud`, `bitcoin-trading` 배포 런북과 절차를 섞지 않는다.
- 특히 `docs/final/SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md`는 no1kmedi/mkmlife용이 아니다.
- `docs/final/MFH_*` 등에 등장하는 **원격 GitHub 조직/레포**(`mkmlab-v2/...`)는 **과거 CI·핸드오프 기록**이다. 현재 `C:\workspace` 모노레포와 **동일 원격이라고 가정하지 않는다**(경로·워크플로 혼동 방지).

### 1.1) 로컬 폴더 역할 (같은 `projects/no1kmedi` 아래)

| 경로 | 역할 |
|------|------|
| `projects/no1kmedi/` | Next.js 앱·CI 대상 (`no1kmedi-web-build` 워크플로 등) |
| `projects/no1kmedi/payapp-api/` | Express `api.no1kmedi.com` 백엔드·스모크·벤치 |
| `projects/no1kmedi/marketing-site/` | 정적 마케팅 자산(별도 빌드 파이프라인) |

`mkmlife.com` 전용 UI가 이 모노레포의 **별도 폴더명**으로 없을 수 있다. VPS에서는 `mkm-life` 등 **별도 클론/빌드 트리**로 돌아갈 수 있으므로, 로컬은 위 표 + **VPS `exec cwd` 실측**으로만 맞춘다.

### 1.2) PM2 이름 혼동 방지 (레포 vs 본선)

| 구분 | 이름 | 비고 |
|------|------|------|
| 레포 `ecosystem.config.cjs` / `deploy-vps-local-llm.sh` | `no1kmedi-payapp-api` | Express `payapp-api`용 |
| 본선 잠금(실측) | `no1kmedi-com` | Next standalone (`…/.next/standalone`) — **Express와 별 프로세스** |
| 본선 잠금(실측) | `mkmlife` | `mkm-life` 런타임 |

**같은 이름으로 두 서비스를 취급하지 말 것.** 배포·재시작 시 어떤 앱인지 먼저 구분한다.

## 2) 로컬 SSOT 경로 (검증 완료)

- 워크스페이스 루트: `C:\workspace`
- no1kmedi 웹·API 작업 진입점: `C:\workspace\projects\no1kmedi\` (Next) 및 `C:\workspace\projects\no1kmedi\payapp-api\` (Express)
- Express API 주요 파일:
  - `projects/no1kmedi/payapp-api/server.js`
  - `projects/no1kmedi/payapp-api/.env.example`
  - `projects/no1kmedi/payapp-api/ecosystem.config.cjs`
  - `projects/no1kmedi/payapp-api/deploy-vps-local-llm.sh`

### 2.1) 로컬 드라이브 정책 (지휘관 확정)

- **작업·Cursor 워크스페이스 SSOT**: `C:\workspace` 모노레포와 **동일 트리**에서 진행한다. 에이전트·문서·스크립트 기본 경로가 이 루트를 전제로 한다.
- **E: / F:**: **보관·백업·아카이브 전용**. 일상 개발·배포 준비의 1차 작업 트리로 쓰지 않는다(복사본·스냅샷·오프로드용).
- **전환 시**: 과거에 `E:\workspace\mkm-life` 등으로 열어두었다면, **File → Open Folder**로 `C:\workspace`(또는 해당 모노레포 루트)를 연 뒤 터미널 기본 cwd도 그 경로로 맞춘다.

### 2.2) `deploy-to-hostinger.ps1` (모노레포 밖 — 실측 잠금)

- **`C:\workspace` 트리 안에는 없음.** (Glob·검색으로 확인.)
- **실제 위치(디스크 실측)**: `E:\workspace\mkm-life\deploy-to-hostinger.ps1` — mkmlife.com용 Hostinger VPS 배포 v2 스크립트. **수동 실행**(자동 배포 아님). 기본 `$PSScriptRoot`·상위 `E:\workspace\.env`의 `GEMINI_API_KEY` 등을 참조한다.
- **SSH 키 기본값**: 스크립트가 User 환경변수 `VPS_SSH_KEY` 미설정 시 `F:\workspace\.ssh\hostinger_mkmlife`를 본다. 키·호스트는 **본인 환경변수(`VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`) 우선**.
- **스크립트의 원격 배포 루트**: 스크립트 내 `$VPS_PATH = /var/www/mkmlife` (frontend/backend 등 하위 구조). 이 값과 §3 PM2 잠금 경로(`/var/www/mkmlife_runtime/mkm-life`)는 **문자열이 다를 수 있다.** 운영·헬스 판정은 항상 **`pm2 describe` 실측** 우선.
- **Hostinger API MCP(레포)**: `scripts/run_hostinger_mcp.ps1` — 배포 스크립트와 **역할 다름**(MCP 러너).

**수동 실행 예시(Windows, 자동 배포 아님):**

```powershell
Set-Location E:\workspace\mkm-life
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy-to-hostinger.ps1 -DryRun
# 실제 반영 시에만 -DryRun 제거. 사전: User 환경변수 VPS_HOST / VPS_USER / VPS_SSH_KEY 및 SSH 키 파일 존재 확인.
```

**SSH 한 줄·따옴표 실수 방지(모노레포, 배포 아님):** `C:\workspace`에서 `scripts/Invoke-MkmlifeVpsGitProbe.ps1` — `VPS_HOST` 플레이스홀더·빈 키 경로를 사전에 거부하고, 원격 `cd … && git …`를 **단일 인자**로 `ssh`에 넘긴다 (`VPS_HOST`/`VPS_USER`는 **실제 IP·호스트명·계정**만).

- **E: 예외**: 일상 편집은 `C:\workspace` 정책을 따르되, **이 스크립트가 현재 E:\ 클론에만 있으면** 배포 실행 시에 한해 `E:\workspace\mkm-life`로 이동한다. 나중에 스크립트를 모노레포로 옮기면 이 절 경로만 갱신한다.

### 2.3) GitHub Actions(레포 내, push/수동 실행 시만)

| 워크플로 | 용도 |
|----------|------|
| `.github/workflows/no1kmedi-api-smoke.yml` | `projects/no1kmedi/payapp-api` 스모크·원격 API |
| `.github/workflows/no1kmedi-web-build.yml` | `projects/no1kmedi` Next 빌드 검증 |

CI는 **저장에 포함된 워크플로만** 돌아간다. §2.2의 `deploy-to-hostinger.ps1`은 **GitHub Actions가 아니라 로컬 PS 수동 실행** 경로다.

## 3) VPS 경로 SSOT 잠금값 (PM2 실측)

절대경로는 추측하지 않고, PM2 `exec cwd` 실측값으로만 고정한다.

- `no1kmedi-com` PM2 `exec cwd`: `/opt/no1kmedi-com/.next/standalone`
- `mkmlife` PM2 `exec cwd`: `/var/www/mkmlife_runtime/mkm-life`

운영 규칙:

- 배포/장애 대응 시 위 두 경로를 런타임 기준 SSOT로 사용한다.
- 경로 기준 판정은 `pm2 describe <app>` 출력만 근거로 한다.
- 추정 경로(`/opt/workspace/...` 등)는 문서·명령의 기본값으로 사용하지 않는다.

### 3.1) 동일 호스트에 Git 클론이 둘 이상일 때 (조건부)

- **본선(서비스) Git SSOT**는 **`mkmlife`의 `exec cwd` 트리**뿐이다. 그 디렉터리에서 `git rev-parse HEAD` / `origin/main`만 “지금 나가는 빌드가 따르는 커밋” 판정에 쓴다.
- 같은 VPS에 **참고·에이전트·동기 확인용**으로 모노레포 클론이 **또** 있을 수 있다(예: 일부 호스트에서 `/opt/mkm-sync-check`). 이 경로는 **호스트마다 없거나 이름이 다를 수 있으므로 SSOT로 고정하지 않는다.**
- 그런 클론의 SHA가 `exec cwd` 트리와 **다르더라도** 곧바로 “장애”가 아니다. **수동 배포·검증 대기·롤백 유지**면 정상일 수 있다. 판단은 **SHA 차이 자체**가 아니라 **본선이 따라야 할 브랜치(보통 `origin/main`)**와 **누가·언제 pull/build/restart 하는지** 한 줄로 한다.
- 해당 보조 경로가 없거나 다르면 **`pm2 describe mkmlife`로 본 `exec cwd`만** 근거로 삼는다.

## 4) VPS 확인 명령 (SSH 접속 후 즉시)

```bash
pwd
pm2 describe no1kmedi-com | sed -n '1,160p'
pm2 describe mkmlife | sed -n '1,160p'
```

확인 기준:

- SSH 직후 현재 위치(`pwd`) 기록
- PM2 `exec cwd`가 잠금값과 일치하는지 확인
- 불일치 시 임의 수정하지 말고, 경로 확정 후 재배포 절차를 다시 밟는다

재등록 예시(주의: 아래는 `ecosystem.config.cjs`가 실제로 존재하는 디렉터리에서만 실행):

```bash
# no1kmedi-com (예: ecosystem 파일이 있는 경로)
cd /opt/no1kmedi-com
pm2 delete no1kmedi-com || true
pm2 start ecosystem.config.cjs --name no1kmedi-com
pm2 save

# mkmlife (예: ecosystem 파일이 있는 경로)
cd /var/www/mkmlife_runtime/mkm-life
pm2 delete mkmlife || true
pm2 start ecosystem.config.cjs --name mkmlife
pm2 save
```

## 5) 배포/점검 단일 플로우 (ChatGPT 방식 체크리스트)

1. SSH 접속 직후 `pwd` + `pm2 describe no1kmedi-com` + `pm2 describe mkmlife` 실행
2. `pwd` 기준 경로가 Git 레포일 때만 `git pull origin main` 실행
3. `.env` 확인 (`LOCAL_LLM_URL`, `AI_ROUTER_MODE` 등)
4. **Express API만** `payapp-api` 디렉터리에서 `./deploy-vps-local-llm.sh` 실행(PM2 이름 `no1kmedi-payapp-api`). `no1kmedi-com` / `mkmlife` 배포는 각각 해당 빌드·호스트 절차를 따른다.
4b. **mkmlife.com(Hostinger VPS) 프론트 배포(로컬 Windows)**: §2.2의 `deploy-to-hostinger.ps1`를 **수동** 실행(-DryRun 권장 선행). VPS 반영 후 §4처럼 `pm2 describe mkmlife`로 실측 확인.
5. `pm2 describe <app>`에서 `exec cwd`, `status` 확인
6. `curl -sS https://api.no1kmedi.com/api/ai/router-status` 확인

## 6) 이번 정리 결론

- no1kmedi/mkmlife **로컬 작업 트리 SSOT**는 `projects/no1kmedi/`(Next 등) + `projects/no1kmedi/payapp-api/`(Express)로 고정한다.
- 로컬은 `C:\workspace` 모노레포 트리를 1차 작업 기준으로 하고, E:/F:는 보관용으로만 쓴다.
- jema12/jemaai 런북과 절차 혼용 금지를 문서로 명시했다.
- VPS 런타임 SSOT는 PM2 실측 `exec cwd` 잠금값으로 고정한다.

## 7) 운영용 1페이지 체크 커맨드 (복붙용)

```bash
# 0) SSH 접속 직후: 경로 실측
pwd
pm2 describe no1kmedi-com | sed -n '1,160p'
pm2 describe mkmlife | sed -n '1,160p'

# 1) no1kmedi-com: exec cwd 확인
# 기대: /opt/no1kmedi-com/.next/standalone

# 2) mkmlife: exec cwd 확인
# 기대: /var/www/mkmlife_runtime/mkm-life

# 3) 현재 pwd가 Git 레포면만 최신 반영
git rev-parse --is-inside-work-tree && git pull origin main || echo "skip git pull (not a git repo)"

# 4) 배포 스크립트(존재하는 경우)
test -f ./deploy-vps-local-llm.sh && bash ./deploy-vps-local-llm.sh || echo "deploy script not in current dir"

# 5) 상태 재확인
pm2 describe no1kmedi-com | sed -n '1,120p'
pm2 describe mkmlife | sed -n '1,120p'
curl -sS https://api.no1kmedi.com/api/ai/router-status
```

## 8) 3줄 판정 규칙 (실행 결과용)

- **정상**: `no1kmedi-com`/`mkmlife`의 PM2 `exec cwd`가 잠금값과 일치하고, `router-status`가 200 계열 응답.
- **주의**: PM2 앱은 살아 있으나 `exec cwd` 불일치 또는 `git pull`/배포 스크립트가 `skip`된 경우.
- **수정 필요**: PM2 앱 down/error, `exec cwd` 미일치 + 서비스 응답 실패(5xx/타임아웃/연결불가).

빠른 체크 포인트:

- `pm2 list`에서 두 앱 status 확인
- `pm2 describe <app>`의 `exec cwd` 확인
- `curl -sS https://api.no1kmedi.com/api/ai/router-status` 응답 확인
