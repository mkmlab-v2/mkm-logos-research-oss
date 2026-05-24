#Requires -Version 5.1
<#
.SYNOPSIS
  Copy OPS_ALARM_WEBHOOK_URL from local .env to VPS destiny .env (secrets not printed).

.DESCRIPTION
  Fallback order: OPS_ALARM_WEBHOOK_URL, N8N_WEBHOOK_URL, SLACK_WEBHOOK_URL.
  Then runs Aroon dispatch once on VPS (test POST only if non-HOLD change).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-SyncVpsOpsAlarmWebhook_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$VpsHost = "vps-mkmlife",
    [string]$DestinyRoot = "/opt/mkm-destiny-ai-41e38ec6",
    [switch]$SkipDispatchTest
)

$ErrorActionPreference = "Stop"
$envFile = Join-Path $WorkspaceRoot ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Missing $envFile"
}

$extractPy = Join-Path $env:TEMP "mkm_extract_ops_webhook_v1.py"
@'
import os, sys
from pathlib import Path
p = Path(os.environ["MKM_ENV_FILE"])
keys = ("OPS_ALARM_WEBHOOK_URL", "N8N_WEBHOOK_URL", "SLACK_WEBHOOK_URL")
text = p.read_text(encoding="utf-8", errors="ignore")
found = {}
for line in text.splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    k = k.strip()
    v = v.strip().strip('"').strip("'")
    if k in keys and v and k not in found:
        found[k] = v
url = found.get("OPS_ALARM_WEBHOOK_URL") or found.get("N8N_WEBHOOK_URL") or found.get("SLACK_WEBHOOK_URL")
if not url:
    print("MISSING")
    sys.exit(2)
out = Path(os.environ["TEMP"]) / "mkm_ops_alarm_webhook_line.env"
out.write_text("OPS_ALARM_WEBHOOK_URL=" + url + "\n", encoding="utf-8")
src = "OPS_ALARM" if found.get("OPS_ALARM_WEBHOOK_URL") else ("N8N" if found.get("N8N_WEBHOOK_URL") else "SLACK")
print("OK source=" + src)
'@ | Set-Content -LiteralPath $extractPy -Encoding UTF8

$env:MKM_ENV_FILE = $envFile
$pyOut = py $extractPy 2>&1
Remove-Item -LiteralPath $extractPy -Force -ErrorAction SilentlyContinue
if ($LASTEXITCODE -ne 0) {
    throw "Local .env has no OPS_ALARM/N8N/SLACK webhook URL. Set OPS_ALARM_WEBHOOK_URL in $envFile"
}
Write-Host $pyOut -ForegroundColor Cyan

$patchLocal = Join-Path $env:TEMP "mkm_ops_alarm_webhook_line.env"
$remoteEnv = "$DestinyRoot/.env"
scp $patchLocal "${VpsHost}:/tmp/mkm_ops_alarm_webhook_line.env"
if ($LASTEXITCODE -ne 0) { throw "scp patch failed" }

$remoteCmd = "cd $DestinyRoot && touch .env && (grep -v '^OPS_ALARM_WEBHOOK_URL=' .env > .env.tmp || true) && cat /tmp/mkm_ops_alarm_webhook_line.env >> .env.tmp && mv .env.tmp .env && rm -f /tmp/mkm_ops_alarm_webhook_line.env && grep -q '^OPS_ALARM_WEBHOOK_URL=.' .env && echo VPS_ENV_OK"
ssh $VpsHost $remoteCmd
if ($LASTEXITCODE -ne 0) { throw "VPS .env patch failed" }

Remove-Item -LiteralPath $patchLocal -Force -ErrorAction SilentlyContinue

if (-not $SkipDispatchTest) {
    Write-Host "==> Aroon dispatch probe (loads VPS .env)" -ForegroundColor Cyan
    $dispatchCmd = "cd $DestinyRoot && set -a && . ./.env && set +a && cd projects/bitcoin-trading && python3 scripts/dispatch_aroon_signal_webhook_v1.py"
    ssh $VpsHost $dispatchCmd
    $grepCmd = "grep -E webhook_configured\|dispatch $DestinyRoot/projects/bitcoin-trading/memory/v2/ops/aroon_signal_webhook_dispatch_latest.json 2>/dev/null | head -5 || true"
    ssh $VpsHost $grepCmd
}

Write-Host "DONE Invoke-SyncVpsOpsAlarmWebhook_v1" -ForegroundColor Green
