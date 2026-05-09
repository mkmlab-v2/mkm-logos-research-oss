# AGENTS — projects/bitcoin-trading (배포 트리)

> 이 파일은 요약 포인터다. 운영 정책 SSOT는 `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md` 단일 문서로 통일한다.

**역할**: 모노레포 안의 **트레이딩·운영 코드 묶음**이다. VPS 본선에서는 `/opt/bitcoin-trading` 등으로 체크아웃되는 경우가 많다. 전역 에이전트 규칙은 **저장소 루트** `AGENTS.md`와 `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`가 우선한다.

## 로컬 vs VPS (본선 전용, 5줄)

1. **코드·규칙은 Git만.** 로컬에서 편집·테스트 후 `push`. VPS에서는 **소스 직접 수정 금지** — 실수로 고쳤으면 **로컬에 반영·`push`한 뒤** 서버에서 `git checkout -- .` 등으로 **레포 상태로 되돌린다**.
2. **VPS 작업 순서:** `git pull` → (런북에 적힌 **빌드/설치**가 있으면 실행) → **`pm2 restart <런북에 적힌 앱 이름>`** 만. **`pm2 restart all` 금지** (런북에 **명시된 경우만** 예외).
3. **`.env` (중요):** `scripts/start_24h_daemon.py`는 **모노레포 루트 `…/workspace/.env`가 있으면 그걸 우선** 읽고, 없으면 레거시 `projects/.env`를 본다. PM2 `cwd`가 모노레포 루트면 **루트 `.env`가 실제 본선 키/스위치**가 된다. 단독 클론으로 `cwd=/opt/bitcoin-trading`만 쓰는 경우엔 그 트리의 `.env`가 우선이다. 어떤 경우든 **Git에 커밋하지 않는다.**
4. **Cursor SSH**: “실행만 하는 주방” — 레시피 수정은 로컬. 비유·공통 원칙: 루트 `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`.
5. **`start_live_trading.py`**: 패키지 루트(`projects/bitcoin-trading/start_live_trading.py`) — **`scripts/start_24h_daemon.py`를 같은 Python으로 subprocess 위임**한다. PM2·런북에서 예전에 VPS 전용 경로만 쓰던 경우, **동일 파일을 Git SSOT로 맞춘다**. 실전 ON 전 점검(비밀 미출력): `powershell -File projects/bitcoin-trading/scripts/preflight_live_trading_readiness.ps1` — PM2 예시: `projects/bitcoin-trading/ops/pm2.ecosystem.example.cjs`.

## 선물 엔진 분기 (레거시 vs 아론 Aroon)

- **스위치:** `BTC_FUTURES_ENGINE` — 비우거나 `legacy` → `RealtimeTradingWithMonitoring`(통합 엔진). **`aroon_v1`** → `src/futures_engine/aroon_futures_engine.py` 만 사용(예언·멀티렌스 스택과 **코드 경로 분리**).
- **주입:** `scripts/start_24h_daemon.py`가 모노레포 루트 `.env`에서 `BTC_FUTURES_ENGINE`·`AROON_*` 를 읽어 `os.environ`에 올린 뒤 데몬이 동일 모드를 로그에 남긴다.
- **VPS:** 배포 트리 `git pull` 후 **`pm2 restart <해당 앱만>`**. PM2 `env` 또는 호스트 `.env`에 `BTC_FUTURES_ENGINE=aroon_v1` 설정. 로그 버퍼 완화: `PYTHONUNBUFFERED=1` 권장(`ops/pm2.ecosystem.example.cjs` 주석 참고).
- **상세 변수:** 루트 `.env.example` 의 `BTC_FUTURES_ENGINE` / `AROON_*` 절.

## 실매매(메인넷 주문) — 재발 방지 체크리스트 (Fact-Lock)

자동으로 “다 된 상태”가 되게 두지 않는다. 아래는 **사람이 실매매로 켠다는 결정** 이후에만 수행한다.

1. **돌아가는 집 확인:** `pm2 describe <앱이름>`에서 **`exec cwd` + `script path`**가 의도한 트리인지 확인한다. `/opt/bitcoin-trading-live`만 고치고 PM2가 `/opt/mkm-lab-workspace-v2`를 쓰는 식이면 **본선은 그대로**일 수 있다. 헷갈리면 `ops/v2/ssh/VPS_PM2_HEALTH_SSH_CURSOR_RUNBOOK.md`의 절차로 스냅샷을 남긴다.
2. **코드 동기:** 그 `cwd` 루트에서만 `git pull` → **`pm2 restart <해당 앱만>`** (`restart all` 금지, 런북 예외만).
3. **스위치(환경 > YAML 기본):** 루트 `.env`(또는 실제 `cwd`의 `.env`)에 **`TESTNET=false`(또는 `0/off`)**, **`ENABLE_TRADING=true`(또는 `1/on`)** — 미설정이면 `config/trading_config.yaml`의 `testnet` / `enable_live_trading`·`enable_trading` 기본값을 따른다(`scripts/start_24h_daemon.py`가 최종 합성).
4. **기동 로그 확인:** `start_24h_daemon.py`가 출력하는 블록에서 **`테스트넷: False (실전 모드)`** + **`거래: 활성화`**가 둘 다 보여야 한다. 둘 중 하나라도 다르면 주문 경로를 신뢰하지 않는다.
5. **키·한도:** 거래소 키는 VPS에만. `config/trading_config.yaml`의 레버리지·포지션 상한·손실 한도가 의도와 일치하는지 확인한다.

로컬(또는 VPS PowerShell)에서 비밀 출력 없이 1회 점검: `powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/scripts/preflight_live_trading_readiness.ps1`

추가 고정 원칙:
- **코드/전략 동기화는 상시 수행**
- **실전 주문 활성화(ON/OFF)는 별도 승인 게이트**

하드라인 게이트(요약):
- `max_drawdown <= -3.0%` 또는 연속 손실 `>= 4회`면 즉시 cooldown
- 주문 ACK `p95 > 1500ms`(10분), API 실패율 `> 5%`(5분)면 신규주문 차단
- `state mismatch` 1건이라도 발생 시 즉시 차단
- 자동 재개 금지(최소 30분 + health 15분 정상 + 승인 플래그)

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

## Trading Guardian (Windows 로컬 자동화)

모노레포 루트 기준: 보호 주문 커버리지·번들 헬스·정책 해시 드리프트·일일 드릴은 **`../../scripts/`** 아래 PS1·파이썬으로 돈다. 정책 템플릿은 **`../../scripts/data/trading_guardian_policy_template_v1.json`** — 최초에는 **`../../scripts/Ensure-TradingGuardianPolicyFromTemplate.ps1`** 로 `reports/trading_guardian_policy_latest.json`(루트 `reports/`, Git 무시)을 채운다.

- 번들·커버리지·정책 감시·드릴 등록 예: `Register-TradingGuardianBundleTask.ps1`, `Register-ProtectiveCoverageGuardTask.ps1`, `Register-TradingGuardianPolicyWatchTask.ps1`, `Register-TradingGuardianDailyDrillTask.ps1`
- 웹훅: `.env` 의 `TRADING_GUARDIAN_BUNDLE_WEBHOOK_URL`, `TRADING_GUARDIAN_POLICY_WEBHOOK_URL`(미설정 시 `OPS_ALARM_WEBHOOK_URL` 폴백 가능)

실매매·메인넷 주문 경로(`execute_binance_usdm_protective_orders_v1.py` 등)는 **본 절의 실매매 체크리스트·승인 게이트**와 별도로 취급한다.

## 더 읽기

- 루트: `../../AGENTS.md` · `../../docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`
- SSH·운영: `ops/v2/LOCAL_MAIN_SSH_OPS_RUNBOOK.md` (실제 `pwd`·PM2 이름은 **실측**)
