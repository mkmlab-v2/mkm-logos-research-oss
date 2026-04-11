# AGENTS — projects/bitcoin-trading (배포 트리)

**역할**: 모노레포 안의 **트레이딩·운영 코드 묶음**이다. VPS 본선에서는 `/opt/bitcoin-trading` 등으로 체크아웃되는 경우가 많다. 전역 에이전트 규칙은 **저장소 루트** `AGENTS.md`와 `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`가 우선한다.

## 로컬 vs VPS (본선 전용, 5줄)

1. **코드·규칙은 Git만.** 로컬에서 편집·테스트 후 `push`. VPS에서는 **소스 직접 수정 금지** — 실수로 고쳤으면 **로컬에 반영·`push`한 뒤** 서버에서 `git checkout -- .` 등으로 **레포 상태로 되돌린다**.
2. **VPS 작업 순서:** `git pull` → (런북에 적힌 **빌드/설치**가 있으면 실행) → **`pm2 restart <런북에 적힌 앱 이름>`** 만. **`pm2 restart all` 금지** (런북에 **명시된 경우만** 예외).
3. **`.env`**: 실행 cwd 기준 `.env`를 우선하고, 본선 루트가 `/opt/bitcoin-trading`이면 **`/opt/bitcoin-trading/.env`** 를 같은 방식으로 둔다. **Git에 커밋하지 않는다.**
4. **Cursor SSH**: “실행만 하는 주방” — 레시피 수정은 로컬. 비유·공통 원칙: 루트 `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`.
5. **`start_live_trading.py`**: 레포 루트(`projects/bitcoin-trading/start_live_trading.py`) — 위 `.env` 순서로 로드한 뒤 **`scripts/start_24h_daemon.py`로 exec**한다. PM2·런북에서 예전에 VPS 전용 경로만 쓰던 경우, **동일 파일을 Git SSOT로 맞춘다**.

## 더 읽기

- 루트: `../../AGENTS.md` · `../../docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`
- SSH·운영: `ops/v2/LOCAL_MAIN_SSH_OPS_RUNBOOK.md` (실제 `pwd`·PM2 이름은 **실측**)
