<#
.SYNOPSIS
  SSH one-shot: VPS 본선(destiny 모노레포)·랩·레거시 클론 상태를 한 번에 출력.

.DESCRIPTION
  경로 SSOT: docs/final/VPS_BITCOIN_LIVE_RUNTIME_POINTER_V1.json
  본선 PM2 cwd 기본값: /opt/mkm-destiny-ai-41e38ec6 (레거시 /opt/bitcoin-trading-live 아님).
  PM2 describe는 bitcoin-live-small-24h 기준(앱 없으면 스킵).
  -PullLabCronDiff 로 랩 트리의 export/sync cursor cron 등록 스크립트 미커밋 diff를
  reports/vps-mkm-lab-cron-export-sync.patch 로 저장.

.PARAMETER VpsHost
  SSH config의 Host 또는 user@host. 기본: 환경변수 VPS_SSH_HOST, 없으면 vps-mkmlife.

.PARAMETER PullLabCronDiff
  랩 모노레포에서 두 cron 셸의 git diff만 로컬 reports로 저장.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-VpsBitcoinLabAndLiveStatus.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-VpsBitcoinLabAndLiveStatus.ps1 -VpsHost vps-mkmlife -PullLabCronDiff
#>
param(
    [string]$VpsHost = $(if ($env:VPS_SSH_HOST) { $env:VPS_SSH_HOST } else { "vps-mkmlife" }),
    [switch]$PullLabCronDiff
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$reportsDir = Join-Path $repoRoot "reports"
if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir | Out-Null
}

$remoteBash = @'
set -euo pipefail
echo "SSOT: VPS_BITCOIN_LIVE_RUNTIME_POINTER_V1.json (repo docs/final)"
echo ""
echo "========================================"
echo "LIVE PRIMARY (destiny monorepo): /opt/mkm-destiny-ai-41e38ec6"
echo "========================================"
if [ -d /opt/mkm-destiny-ai-41e38ec6 ]; then
  cd /opt/mkm-destiny-ai-41e38ec6
  git status -sb || true
  git log -1 --oneline || true
  echo "--- remotes (first 2 lines) ---"
  git remote -v 2>/dev/null | head -n 2 || true
else
  echo "[MISSING] /opt/mkm-destiny-ai-41e38ec6"
fi
echo ""
echo "========================================"
echo "PM2: bitcoin-live-small-24h (authoritative for live cwd)"
echo "========================================"
if command -v pm2 >/dev/null 2>&1; then
  pm2 describe bitcoin-live-small-24h 2>/dev/null | head -n 35 || echo "(app not found or describe failed)"
else
  echo "(pm2 not in PATH)"
fi
echo ""
echo "========================================"
echo "LAB MONOREPO (ship default, not always live cwd): /opt/mkm-lab-workspace-v2"
echo "========================================"
if [ -d /opt/mkm-lab-workspace-v2 ]; then
  cd /opt/mkm-lab-workspace-v2
  git status -sb || true
  git log -1 --oneline || true
  echo "--- branch -vv (first line) ---"
  git branch -vv 2>/dev/null | head -n 1 || true
else
  echo "[MISSING] /opt/mkm-lab-workspace-v2"
fi
echo ""
echo "========================================"
echo "LEGACY standalone clone (do not deploy live here): /opt/bitcoin-trading-live"
echo "========================================"
if [ -d /opt/bitcoin-trading-live ]; then
  cd /opt/bitcoin-trading-live
  git status -sb || true
  git log -1 --oneline || true
else
  echo "[MISSING] /opt/bitcoin-trading-live"
fi
'@
$remoteBash = $remoteBash -replace "`r`n", "`n" -replace "`r", "`n"

$utf8 = New-Object System.Text.UTF8Encoding $false
$b64 = [Convert]::ToBase64String($utf8.GetBytes($remoteBash))
Write-Host ">>> SSH: $VpsHost (two-tree status)" -ForegroundColor Cyan
ssh $VpsHost "echo $b64 | base64 -d | bash"

if ($PullLabCronDiff) {
    $patchPath = Join-Path $reportsDir "vps-mkm-lab-cron-export-sync.patch"
    $r1 = "projects/bitcoin-trading/ops/v2/ssh/register_export_then_sync_cursor_trade_history_cron.sh"
    $r2 = "projects/bitcoin-trading/ops/v2/ssh/unregister_export_then_sync_cursor_trade_history_cron.sh"
    Write-Host ">>> Pulling lab diff -> $patchPath" -ForegroundColor Cyan
    ssh $VpsHost "cd /opt/mkm-lab-workspace-v2 && git diff -- $r1 $r2" | Set-Content -Path $patchPath -Encoding utf8
    if ((Get-Item $patchPath).Length -eq 0) {
        Write-Warning "Patch file is empty (no unstaged diff on VPS for those two paths)."
    }
    else {
        Write-Host "OK: wrote $patchPath ($((Get-Item $patchPath).Length) bytes)"
    }
}
