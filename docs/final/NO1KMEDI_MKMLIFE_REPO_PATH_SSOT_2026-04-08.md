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
| `projects/mkm/mkm-life/` | **mkmlife.com** 소스(Git **서브모듈** `mkmlab-hq/mkmlife-com`). 로컬 1차 편집·빌드 진입점(§2.1a). |

`mkmlife.com` UI는 위 **`projects/mkm/mkm-life`** 서브모듈이 권장 로컬 트리다. VPS 본선은 여전히 **별도 `exec cwd`**(`/var/www/mkmlife_runtime/mkm-life` 등)일 수 있으므로, 경로·커밋 일치는 **`pm2 describe` 실측**과 `git rev-parse`로만 판정한다.

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

### 2.1a) 모노레포 내 `mkm-life` (mkmlife-com) — 권장 로컬 작업 트리

- **경로:** `C:\workspace\projects\mkm\mkm-life`
- **원격:** `git@github.com:mkmlab-hq/mkmlife-com.git` (루트 `.gitmodules`의 서브모듈 `projects/mkm/mkm-life`와 동일)
- **초기화(클론 직후·동료 머신):** 모노레포 루트에서 `git submodule update --init projects/mkm/mkm-life`
- **역할:** mkmlife.com 프론트·§10·§11 제품 락 구현의 **로컬 편집 SSOT**. 배포는 §2.2 `deploy-to-hostinger.ps1`(E: 등)·VPS 절차로 본선에 반영하며, **배포 루트 문자열과 로컬 폴더 경로가 다를 수 있음**(§3 `exec cwd` 실측 우선).
- **VPS·SSH Cursor 정리(공유 드라이브·아티팩트와 본선 분리):** `docs/final/MKMLIFE_VPS_SSH_CURSOR_CLEANUP_RUNBOOK.md`

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
- **철거(단일 SSOT 권장):** 보조 클론이 혼선만 남긴다고 판단되면, **`mkmlife`의 `exec cwd`가 `/opt/mkm-sync-check` 아님**을 `pm2 describe`로 확인한 뒤 제거한다. (다른 용도로 쓰는 디렉터리면 절대 삭제하지 않는다.)

**VPS bash 복붙 — 옵션 A(정찰용 클론 제거) 한 블록:**

```bash
pm2 describe mkmlife | grep -E 'exec cwd|status'
test -d /opt/mkm-sync-check && rm -rf /opt/mkm-sync-check && echo "OK: removed /opt/mkm-sync-check" || echo "OK: path already absent"
```

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

## 9) Git stash · 동기 (로컬 모노레포 + VPS + 전용 클론) — 융합 절차

**원칙:** `stash@{n}` 내용을 `show`로 확인하기 전에는 **`pop`/`drop` 자동화 금지**. 맨 위 stash가 `docs/final/artifacts` 등 **대량 아티팩트**이면 실수 시 복구 비용이 크다.

### 9.1) 로컬 `C:\workspace` (모노레포)

1. 동기 확인(해시는 매번 `git rev-parse`로 확인; 문서에 고정 커밋을 박아 넣지 않는다):

```powershell
Set-Location C:\workspace
git fetch origin
git rev-parse --short HEAD
git rev-parse --short origin/main
git status -sb
```

2. stash 목록·내용 엿보기(PowerShell에서는 ref를 **따옴표**로 감싼다):

```powershell
git stash list
git stash show --stat 'stash@{0}'
# 필요 시: git stash apply 'stash@{0}'   # 또는 pop / drop — 정책 확정 후 수동만
```

3. **에이전트/스크립트:** `stash` **일괄 `drop`/`pop` 금지**(지휘관 확인 전).

### 9.2) VPS `mkmlife` 런타임 경로 (`/var/www/mkmlife_runtime/mkm-life`)

SSH에서만 실행(복붙):

```bash
cd /var/www/mkmlife_runtime/mkm-life
git stash list
git stash show --stat 'stash@{0}'
git stash show --stat 'stash@{1}'
# 필요 시: git stash apply 'stash@{0}'   또는 pop / drop (정책 확정 후)
```

### 9.3) 별도 클론 (`origin` = `mkmlab-hq/mkmlife-com` 등)

**그 레포의 루트 디렉터리**에서 위와 **동일 순서**(`list` → `show` → `apply`/`drop`)를 적용한다. 경로는 VPS·로컬 실측이 SSOT이며, 모노레포 `C:\workspace`와 혼동하지 않는다.

### 9.4) 본 문서 §7과의 관계

- §7: PM2·`git pull`·`router-status` **가동 점검**.
- §9: **stash·로컬/VPS 클론 분리** 등 Git 위생만 담당. 절차를 한 흐름으로 쓸 때는 §7 직후 §9를 붙여 실행한다.

---

## 10) mkmlife UI · 면책 배지 (초안, 제3전선 Last Mile)

**역할 분담:** §1~§9는 **배포·경로·PM2·Git** SSOT이다. 본 절(§10)은 **프론트에 표시할 경고 문구의 초안(draft)** 만 고정한다. **의료·금융 광고·표시 광고** 등 관할 법령과 대외 채널에 맞는 최종 문구는 **법무·운영 검토 후** 확정한다. 에이전트·문서는 본 초안을 **법적 확정문**으로 서술하지 않는다.

**중복 SSOT 방지:** 배포가 어느 레포·어느 `exec cwd`에서 이루어지는지는 **위 표·§7**이 우선이다. `projects/mkm/mkm-life` 등 **별도 트리**가 실측이면 그 경로가 해당 호스트의 SSOT이며, 본 절은 UI 카피만 다룬다.

### 10.1) 필수 배지 ID · 권장 워딩 (초안)

| ID | 권장 노출 | 초안 워딩 (한국어) |
|----|-----------|-------------------|
| `[NON-MEDICAL]` | 사상·체질·건강 관련 해석이 있는 모든 화면 하단 또는 모달 | 본 서비스는 사상의학에 기반한 철학적·교육적 통찰을 제공할 뿐이며, 한의사 등 전문 의료인의 **진단·처방·치료를 대체하지 않습니다**. 증상이 있으면 의료기관을 방문하십시오. |
| `[NON-DETERMINISTIC]` | 명리·운세·주기 해석이 있는 화면 | 명리학적 분석은 **확률적 경향**을 나타낼 수 있을 뿐이며, **결정론적 미래·절대적 길흉**을 보장하지 않습니다. |
| `[FINANCIAL-RISK]` | 거시·시장·자산 관련 인사이트를 노출하는 화면 | 본 서비스의 시장·거시 정보는 **참고용**이며, 투자 권유가 아닙니다. **투자 결과에 대한 법적 책임을 지지 않습니다.** |

### 10.2) 구현 시 체크리스트

- 배지는 **고정 문자열**(위 표)을 쓰거나, 제품에서 **동일 의미**로 번역·축약할 때는 변경 이력을 남긴다.
- B-track·일반 예언·금융 레일과 **동일 API로 합산하지 않는다**(격벽). UI는 **표시 전용**이다.
- 대외 마케팅·스토어 등재 문구는 본 절과 **별도 검토**한다.

### 10.3) 부록: UI 컴포넌트 명세 및 폴백 시나리오 (엔지니어링 초안)

프론트엔드 구현 전 에이전트·개발자가 공유하는 **최소 데이터·UI 계약**이다. 법적 확정문은 §10 본문·법무 검토 후 별도 반영한다.

#### 10.3.1) 핵심 방어 컴포넌트 (이름은 구현체 예시)

| 컴포넌트명 | 역할 및 렌더링 규칙 | 필수 Prop (권장) |
|------------|---------------------|------------------|
| **`DisclaimerPanel`** | §10.1의 `[NON-MEDICAL]` · `[NON-DETERMINISTIC]` · `[FINANCIAL-RISK]` 중, 해당 화면에 적용할 배지 ID를 **항상** 노출. 전역 푸터 또는 결과 카드 **직상단** 권장. 배지 영역은 **비닫기**(dismiss 불가). | `badgeIds: Array<'NON-MEDICAL' \| 'NON-DETERMINISTIC' \| 'FINANCIAL-RISK'>` (표시할 ID만; 카피는 §10.1 SSOT 문자열과 매핑) |
| **`ConfidenceBadge`** | 백엔드가 `confidence`·유사 필드를 제공할 때만 사용. **80 이상**·**50–79**·**50 미만** 구간을 색상/라벨로 구분(예: High / Mid / Low·Hold). 필드가 없으면 **렌더 생략** 또는 스켈레톤 금지(빈 상태 명시). | `score?: number` (optional) |
| **`LensReportCard`** | 로고스·명리·사상 등 **탭 또는 병렬 패널** 컨테이너. 렌즈별 텍스트·수치는 **나란히 표시**하고, **단일 확정 점수로 혼합(블렌드)·단일 예언처럼 합성 표기하지 않는다**(멀티렌즈 격벽). | `lenses: Record<string, { title: string; body: string; meta?: Record<string, unknown> }>` (스키마는 제품 API 확정 시 정교화) |

#### 10.3.2) 상태 머신 및 에러 폴백

프론트는 백엔드 지연·실패·가드레일에 대해 아래 **4가지 뷰**를 구분한다. 스택 트레이스·내부 호스트명·원시 JSON은 **사용자에게 노출하지 않는다**.

| 상태 | 조건(예시) | UI | 카피(초안) |
|------|------------|-----|------------|
| **Loading** | 요청 직후 ~ 첫 응답 전 | 스켈레톤·진행 표시 | "다중 렌즈(로고스·명리·사상)를 통해 지형도를 분석 중입니다…" |
| **Success** | 2xx + 본문 파싱 성공 | `LensReportCard` + 해당 화면에 맞는 `DisclaimerPanel` | §10.1 배지 문구 |
| **Timeout / API 실패** | 네트워크 오류·5xx·타임아웃 | 회색 톤 안내 카드, 재시도 버튼(선택) | "현재 분석 엔진과 연결할 수 없습니다. 잠시 후 다시 시도해 주십시오." |
| **Guardrail blocked** | 백엔드가 정책·안전 기준으로 출력 거부 | 붉은 톤 경고 패널, 입력 수정 유도 | "시스템 안전 기준에 의해 출력이 차단되었습니다. 입력하신 질문을 수정해 주십시오." |

#### 10.3.3) 구현 메모

- 배지 카피는 **§10.1 표만** SSOT로 두고, 컴포넌트는 ID→문자열 매핑 테이블을 한 곳에 둔다.
- 본 부록은 **엔지니어링 초안**이며, 접근성·다국어·스토어 심사 요구는 별도 검토한다.

---

## 11) MKMLIFE 비즈니스 모델 및 핵심 UX (One-Question Premium)

**역할 분담:** §1~§9는 **배포·경로·PM2·Git** SSOT, §10은 **면책·UI 방어 컴포넌트** 초안이다. 본 절(§11)은 **mkmlife.com B2C 상용**의 **제품 정체성·과금 모델·퍼널**만 고정한다. 구현·법무 최종 문구는 §10·별도 검토와 함께 맞춘다.

- **핵심 정체성:** mkmlife.com은 범용 AI 챗봇(월정액·무제한 대화)이 아니며, 사용자의 **단 하나의 중대한 질문(One-Question)** 에 대해 다중 렌즈(Logos / Myeongri / Sasang 등) 엔진을 동원해 **고해상도 맞춤 리포트**를 제공하는 **단건 과금(Pay-per-question) 프리미엄 서비스**다.
- **혼선 방지 락(Lock):** 본 B2C 상용 도메인(mkmlife.com)에는 B2B 투자 쇼룸(jemaai.cloud 등), 한의원 예약·클리닉 전용 흐름, 연구용 벤치마크·내부 옵스 화면을 **혼재하지 않는다**. 사용자에게 보이는 퍼널은 **질문 입력 → 결제 → 프리미엄 리포트 출력**의 **단일 경로**만 둔다(내부 구현은 모노레포·복수 API일 수 있으나 **제품 경험은 하나**).
- **UI 카피 원칙:** 랜딩·온보딩 메시지는 **「가장 중요한 질문 하나에, 다중 렌즈가 융합된 단일 리포트」** 로 귀결되게 쓴다. **월정액·뷔페형** 연상 문구와 **범용 채팅이 주역인 UX**는 기본값으로 두지 않으며, **연속 대화형 Chat UI** 대신 **리포트 청구(Request Report)** 형식의 단건 완결 UX를 제품 기본으로 둔다(§10의 `LensReportCard`·`DisclaimerPanel` 등과 정합).

**금지(본 절 기준):** mkmlife.com 랜딩·핵심 플로우에서 **실거래·투자 지시**, **진료 예약·원격 진단 연결**을 동일 화면 퍼널로 끌어오는 것. 경로·배포 SSOT는 §1~§9, 면책·배지는 §10을 따른다.
