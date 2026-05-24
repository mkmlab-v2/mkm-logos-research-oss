# VPS PM2 health check — SSH Cursor 1-page runbook

**전제:** 이 경로는 모노레포에 포함됩니다. 브랜치 `chore/orchestration-gate-runbook-lock`에서 PM2 점검 스크립트·본 런북을 받습니다(스크립트 커밋 `e942d4d7` 이상, 런북 문서는 `96e992ab` 이상 권장).  
**답:** 네, **VPS 셸(SSH Cursor 터미널)에서 아래만 실행**하면 됩니다. 로컬 Windows만으로는 완료할 수 없습니다.

**두 트리 혼동 방지(로컬에서 한 방):** 모노레포 루트에서 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-VpsBitcoinLabAndLiveStatus.ps1` — SSH 대상은 `$env:VPS_SSH_HOST` 없으면 `vps-mkmlife`. 랩 트리의 export/sync cursor cron 스크립트 미커밋 diff만 PC로 받으려면 `-PullLabCronDiff` (`reports/vps-mkm-lab-cron-export-sync.patch`).

---

## 0) 완료 정의 (DoD)

- [ ] `git`으로 위 브랜치/스크립트가 반영됨
- [ ] 두 `.sh`에 실행 권한 있음
- [ ] `vps_pm2_bitcoin_live_health_snapshot.sh` 실행 → **exit 0** (또는 출력에 `verdict: GO` / `VERDICT=GO`)

---

## 1) 모노레포 루트로 이동

VPS에서 **비트코인 런타임이 아니라 git clone 루트**(모노레포)로 이동합니다.  
(예: `/opt/mkm-lab-workspace-v2`, `/root/apps/mkm-lab-workspace-v2` 등 — 실제 clone 루트로 바꿈)

```bash
# 예시 — 실제 모노레포 루트로 바꾸세요
cd /opt/mkm-lab-workspace-v2
# 또는: cd /root/apps/mkm-lab-workspace-v2
```

---

## 2) 스크립트가 들어온 브랜치 맞추기

```bash
git fetch origin
git checkout chore/orchestration-gate-runbook-lock
git pull --ff-only origin chore/orchestration-gate-runbook-lock
```

**확인(선택):** 최신 커밋에 `ops(ssh): add PM2 bitcoin-live health snapshot` 가 보이면 OK.

```bash
git log -1 --oneline
```

---

## 3) 스크립트 경로 확인

```bash
test -f projects/bitcoin-trading/ops/v2/ssh/vps_pm2_bitcoin_live_health_snapshot.sh && echo "OK: snapshot" || echo "FAIL: missing"
test -f projects/bitcoin-trading/ops/v2/ssh/vps_pm2_bitcoin_live_drift_watch.sh && echo "OK: drift" || echo "FAIL: missing"
```

- 둘 다 `FAIL`이면: **repo 루트가 아님**이거나 **pull 브랜치가 잘못됨** → 1~2단계 재확인.
- **본선 PM2 cwd**는 vps-mkmlife 기준 **`/opt/mkm-destiny-ai-41e38ec6`** (`docs/final/VPS_BITCOIN_LIVE_RUNTIME_POINTER_V1.json`). `/opt/bitcoin-trading-live`는 **레거시** 단독 클론이다.
- cwd에 `projects/bitcoin-trading`가 없으면: **destiny 모노레포에서 pull**하거나, PC에서 두 파일만 같은 상대 경로로 복사해 동일 구조를 맞춤.

---

## 4) 실행 권한

```bash
chmod +x projects/bitcoin-trading/ops/v2/ssh/vps_pm2_bitcoin_live_health_snapshot.sh \
        projects/bitcoin-trading/ops/v2/ssh/vps_pm2_bitcoin_live_drift_watch.sh
```

---

## 5) 원클릭 스냅샷 (필수)

```bash
bash projects/bitcoin-trading/ops/v2/ssh/vps_pm2_bitcoin_live_health_snapshot.sh
```

- **기대:** 마지막에 `verdict: GO` / `VERDICT=GO`, 종료 코드 `0` (`echo $?` → 0).
- PM2 앱 이름이 다르면: `PM2_APP_NAME=실제이름` 붙여 실행.

**스크립트와 변수 이름:** `vps_pm2_bitcoin_live_health_snapshot.sh`는 **`EXPECT_CWD_PREFIX`(기본 `/opt/mkm-destiny-ai-41e38ec6`)** 와 **`PM2_APP_NAME`(기본 `bitcoin-live-small-24h`)** 로 `pm2 describe`의 cwd·script path를 검사합니다. 레거시 `/opt/bitcoin-trading-live` 트리만 쓸 때는 env로 prefix를 덮어씁니다.

**Destiny 헬스 모니터 PM2 등록:**

```bash
cd /opt/mkm-destiny-ai-41e38ec6
bash projects/bitcoin-trading/ops/v2/ssh/register_destiny_vps_health_monitor.sh
```

레거시 `bitcoin-trading-health-monitor`·`bitcoin-live-watchdog`(`/opt/bitcoin-trading`)는 기동하지 않습니다.

---

## 6) (선택) JSONL 로그 남기기

```bash
mkdir -p /opt/bitcoin-trading-live/logs
HEALTH_LOG=/opt/bitcoin-trading-live/logs/pm2_health_snapshots.jsonl \
  bash projects/bitcoin-trading/ops/v2/ssh/vps_pm2_bitcoin_live_health_snapshot.sh
```

---

## 7) (선택) 30분 × 3회 드리프트 — 세션 끊김 방지

장시간이므로 **tmux** 권장.

```bash
tmux new -s pm2-drift
```

안에서:

```bash
cd /root/apps/mkm-lab-workspace-v2   # 실제 모노레포 루트로 (환경에 맞게)
ROUNDS=3 INTERVAL_SEC=1800 bash projects/bitcoin-trading/ops/v2/ssh/vps_pm2_bitcoin_live_drift_watch.sh
```

분리: `Ctrl+b` → `d`. 다시 붙기: `tmux attach -t pm2-drift`.

---

## 8) 실패 시 빠른 확인

```bash
command -v pm2
pm2 ls
pm2 describe bitcoin-live-small-24h 2>/dev/null | head -40
```

---

**SSH Cursor 지시 한 줄:**  
“모노레포 루트에서 2→5까지 순서대로 실행하고, 5번이 exit 0·GO면 완료로 보고.”
