# AGENTS — projects/bitcoin-trading (배포 트리)

**역할**: 모노레포 안의 **트레이딩·운영 코드 묶음**이다. VPS 본선에서는 `/opt/bitcoin-trading` 등으로 체크아웃되는 경우가 많다. 전역 에이전트 규칙은 **저장소 루트** `AGENTS.md`와 `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`가 우선한다.

## 로컬 vs VPS (본선 전용, 5줄)

1. **코드·규칙은 Git만.** 로컬에서 편집·테스트 후 `push`. VPS에서는 **소스 직접 수정 금지** — 실수로 고쳤으면 **로컬에 반영·`push`한 뒤** 서버에서 `git checkout -- .` 등으로 **레포 상태로 되돌린다**.
2. **VPS 작업 순서:** `git pull` → (런북에 적힌 **빌드/설치**가 있으면 실행) → **`pm2 restart <런북에 적힌 앱 이름>`** 만. **`pm2 restart all` 금지** (런북에 **명시된 경우만** 예외).
3. **`.env`**: 실행 cwd 기준 `.env`를 우선하고, 본선 루트가 `/opt/bitcoin-trading`이면 **`/opt/bitcoin-trading/.env`** 를 같은 방식으로 둔다. **Git에 커밋하지 않는다.**
4. **Cursor SSH**: “실행만 하는 주방” — 레시피 수정은 로컬. 비유·공통 원칙: 루트 `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`.
5. **`start_live_trading.py`**: 패키지 루트(`projects/bitcoin-trading/start_live_trading.py`) — **`scripts/start_24h_daemon.py`를 같은 Python으로 subprocess 위임**한다. PM2·런북에서 예전에 VPS 전용 경로만 쓰던 경우, **동일 파일을 Git SSOT로 맞춘다**.

## VPS 모노레포 경로 (Fact-Safe·배포 — 혼동 방지)

- 로컬 `ship_to_vps.ps1` 기본 **VPS 레포 루트**는 **`/opt/mkm-lab-workspace-v2`** (`VpsRepoPath`). 다른 경로(`/opt/mkm-destiny-*` 등)에 클론이 더 있어도, **PM2가 실제로 쓰는 cwd**가 본선이다.
- **반드시** `pm2 show <앱이름>`으로 `exec cwd`·`script path`를 확인한 뒤, 그 모노레포 루트에서만 `git pull`·`scripts/sync_fact_safe_risk_profile.py`·`memory/v2/risk/` 갱신을 한다. 다른 클론에서만 sync 하면 **본선 프로세스가 그 JSON을 읽지 않을 수 있다.**
- 금융 예언 → 리스크 JSON 반영 절차: **`docs/final/FINANCIAL_PROPHECY_VPS_LIVE_TRADING_DIRECTIVE_V1.md`**.

## Git 배포 정렬 (원격·브랜치 혼동 방지)

- **전역 정책**: GitHub 최소·**internal/gitea 우선**은 루트 `AGENTS.md`와 동일. 아래는 **그 VPS가 실제로 fetch하는 원격이 GitHub일 때**만 예외적으로 맞춘다.
- **단일 포인터**: `ops/v2/DEPLOY_GIT_POINTER_V1.json` — 배포 대상이 따라야 할 **remote 이름·브랜치·풀 후 존재해야 할 파일**(bitcoin-trading 기준 상대경로)을 적어 둔다. 호스트마다 다르면 **그 호스트에 맞게 이 JSON만 수정**한다.
- **배포 후 스모크 (VPS, bitcoin-trading이 cwd)**:  
  `bash ops/v2/ssh/check_vps_deploy_files_vs_pointer.sh`  
  exit 0이면 필수 파일이 있다. MISSING이면 커밋이 **다른 원격/브랜치**에만 있는 것이니, 포인터의 `deploy_alignment`에 맞춰 pull 하거나 로컬에서 그 브랜치로 반영 후 다시 pull 한다.

## 더 읽기

- 루트: `../../AGENTS.md` · `../../docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`
- SSH·운영: `ops/v2/LOCAL_MAIN_SSH_OPS_RUNBOOK.md` (실제 `pwd`·PM2 이름은 **실측**)
