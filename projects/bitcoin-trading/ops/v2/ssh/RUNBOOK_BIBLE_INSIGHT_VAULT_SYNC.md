# SSH 24/7: `bible_insight_hourly` + 볼트(MKM_DATA_VAULT) 동기화 런북

**대상**: SSH Cursor / Linux VPS  
**상위 문서**: `SSH_VPS_24H_PREP.md`, `ecosystem.ssh.config.cjs`  
**전제**: VPS는 `G:\` 드라이브에 직접 쓸 수 없음. **산출물은 VPS에 쌓고 → Windows(로컬)에서 당겨와 볼트로 복사**하는 2단이 기본이다.

---

## 0) 한 줄 역할

- **SSH**: `pm2`로 `bitcoin-v2-bible-insight-hourly` 상시 + 로그/헬스 확인.
- **Windows**: `scp`/`rsync`로 `memory/v2`·예언 산출물 폴더를 가져온 뒤 `MKM_DATA_VAULT`에 반영 + (선택) `sync_notebooklm_sources_to_mkm_data_vault.ps1`.

---

## 1) 사전 확인 (SSH에서)

```bash
# 경로는 배포에 맞게 조정
BT=/opt/bitcoin-trading
test -d "$BT/.git" && echo "OK bitcoin-trading repo"
command -v pm2 && pm2 -v
test -x "$BT/.venv/bin/python" && echo "OK venv"
```

**성경 배치 스크립트**: 기본값은  
`/opt/workspace/scripts/final_prophecy_apocalypse_2026.py`  
레포에 없을 수 있으므로 **실제 파일 존재**를 확인한다.

```bash
test -f /opt/workspace/scripts/final_prophecy_apocalypse_2026.py && echo "OK apocalypse script" || echo "MISSING: clone workspace repo or set BIBLE_INSIGHT_COMMAND"
```

없으면 (1) 워크스페이스 루트를 `/opt/workspace`에 클론하거나 (2) 아래 4절에서 `BIBLE_INSIGHT_COMMAND`를 실제 엔트리포인트로 바꾼다.

---

## 2) 최초 부트스트랩 (필요 시만)

```bash
cd /opt/bitcoin-trading
export REPO_URL='https://github.com/YOUR_ORG/YOUR_REPO.git'   # 실제 URL
bash ops/v2/ssh/bootstrap_vps.sh /opt/bitcoin-trading
```

---

## 3) 필수 환경변수 (execute 가드 등)

```bash
export EXECUTE_APPROVAL_HMAC_KEY='(강한 시크릿)'
# 선택: 외부 메모리
# export EXTERNAL_MEMORY_ENABLED=true
# export EXTERNAL_MEMORY_BACKEND=mkm_local
```

---

## 4) Bible 전용 명령 오버라이드 (스크립트 경로가 다를 때)

`ecosystem.ssh.config.cjs`는 `BIBLE_INSIGHT_COMMAND`를 `os.path.expandvars`로 펼친다.  
PM2에 넘기려면 **ecosystem을 수정**하거나, 동일 내용의 로컬 ecosystem 복사본을 쓴다.

예시 (인라인 테스트 — PM2 없이 1회 실행):

```bash
cd /opt/bitcoin-trading
export BIBLE_INSIGHT_COMMAND="/opt/bitcoin-trading/.venv/bin/python /opt/workspace/scripts/final_prophecy_apocalypse_2026.py"
# 루프 없이 스크립트만 검증:
eval "exec $BIBLE_INSIGHT_COMMAND"
```

---

## 5) PM2로 24/7 스택 기동 (bible 포함)

```bash
cd /opt/bitcoin-trading
pm2 start ops/v2/ssh/ecosystem.ssh.config.cjs
pm2 save
pm2 startup    # 출력되는 sudo 명령을 한 번 실행(최초만)
```

**Bible 루프만** 재시작/로그:

```bash
pm2 restart bitcoin-v2-bible-insight-hourly
pm2 logs bitcoin-v2-bible-insight-hourly --lines 200
pm2 describe bitcoin-v2-bible-insight-hourly
```

**Bible만 잠시 끄기** (다른 태스크 유지):

```bash
pm2 stop bitcoin-v2-bible-insight-hourly
```

---

## 6) 헬스 확인

```bash
cd /opt/bitcoin-trading
./.venv/bin/python ops/v2/reports/check_ops_health.py
cat memory/v2/ops/task_health_latest.json 2>/dev/null || true
pm2 status
```

### 정상 로그 패턴 (운영 기준선)

`bitcoin-v2-bible-insight-hourly`가 정상일 때 out 로그에는 아래 3줄이 같은 사이클로 찍힌다.

```text
[...Z] [bible_insight] env_snapshot PYTHONPATH=... PWD=... BIBLE_INSIGHT_COMMAND=...
[...Z] [bible_insight] run_start command=/opt/bitcoin-trading/.venv/bin/python /opt/mkm-lab-workspace-v2/scripts/final_prophecy_apocalypse_2026.py
[...Z] [bible_insight] run_end exit_code=0
```

`run_end exit_code=1` 또는 `No module named 'tools'`가 재발하면, `pm2 env <id>`의 `PYTHONPATH`가  
`/opt/workspace:/opt/mkm-lab-workspace-v2:/opt/bitcoin-trading:/opt/bitcoin-trading/src`인지 먼저 확인한다.

---

## 7) 산출물 위치 (볼트로 옮길 대상)

| 구분 | VPS 상 경로 (기본) | 비고 |
|------|-------------------|------|
| Ops v2 메모리 | `/opt/bitcoin-trading/memory/v2/**` | 브리프, digest, manifest 등 |
| 통합 코드가 기대하는 예언 JSON | 워크스페이스 루트 기준 `docs/prophecy/final_prophecy_apocalypse_2026_*.json` | 스크립트가 **다른 경로**에 쓰면 그 경로를 런북에 메모해 둘 것 |

`vault_sync_manifest.json` 생성 로직은 `ops/v2/connectors/vault_sync.py` — 그래프 러너 등에서 갱신될 수 있음. 볼트 반영 시 `memory/v2/vault_sync_manifest.json` 포함 권장.

---

## 8) VPS → Windows → MKM_DATA_VAULT (볼트 동기화)

### 8A) Windows에서 VPS에서 당기기 (PowerShell)

`VPS_USER`, `VPS_HOST`, 로컬 수신 폴더를 본인 환경에 맞게 바꾼다.

```powershell
$VPS = "VPS_USER@VPS_HOST"
$LocalStaging = "C:\workspace\staging\vps_bitcoin_trading"
New-Item -ItemType Directory -Force -Path $LocalStaging | Out-Null

# memory/v2 전체
scp -r "${VPS}:/opt/bitcoin-trading/memory/v2" "$LocalStaging\memory_v2"

# 예언 JSON/MD가 docs/prophecy 아래에 쌓이는 배포라면 (경로는 실제 스크립트 출력에 맞출 것)
scp -r "${VPS}:/opt/workspace/docs/prophecy" "$LocalStaging\docs_prophecy" 2>$null
```

### 8B) 스테이징 → MKM_DATA_VAULT

```powershell
$Vault = "G:\공유 드라이브\MKM_DATA_VAULT"
$Dest = Join-Path $Vault "vps_artifacts\bitcoin_trading"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Copy-Item -Path "C:\workspace\staging\vps_bitcoin_trading\*" -Destination $Dest -Recurse -Force
```

이후 NotebookLM용 소스 매니페스트에 `vps_artifacts\...` 파일을 넣었으면 로컬 워크스페이스에서:

```powershell
cd C:\workspace
.\scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1
```

(매니페스트에 해당 경로가 없으면 8B만으로도 볼트에 보관 가능.)

---

## 9) SSH Cursor에게 시킬 때 붙여넣을 “작업 지시” 요약

1. `/opt/bitcoin-trading` 최신 `git pull`, `bootstrap_vps.sh` 필요 시 실행.  
2. `final_prophecy_apocalypse_2026.py` 존재 확인; 없으면 `/opt/workspace` 클론 또는 `BIBLE_INSIGHT_COMMAND` 수정.  
3. `EXECUTE_APPROVAL_HMAC_KEY` 등 필수 env 설정.  
4. `pm2 start ops/v2/ssh/ecosystem.ssh.config.cjs` → `pm2 save` → `pm2 startup`.  
5. `pm2 logs bitcoin-v2-bible-insight-hourly`로 첫 1~2사이클 에러 없음 확인.  
6. `check_ops_health.py` 및 `task_health_latest.json` 확인.  
7. 산출물 경로를 메모해 두고, 사용자가 8A/8B로 볼트로 당기게 안내.

---

## 10) 주기 조정

`ecosystem.ssh.config.cjs`의 `bitcoin-v2-bible-insight-hourly` 항목에서  
`--interval-sec 3600`을 변경 후:

```bash
pm2 delete bitcoin-v2-bible-insight-hourly
pm2 start ops/v2/ssh/ecosystem.ssh.config.cjs --only bitcoin-v2-bible-insight-hourly
pm2 save
```

(또는 ecosystem 수정 후 `pm2 reload ecosystem...`.)
