#Requires -Version 5.1
<#
.SYNOPSIS
  RQ-027 chain: dev day pack → Trust Packet v2 sync → pet KV/bridge stub (dry-run).

.DESCRIPTION
  B-track [HYPO]. Default: bridge dry-run + local KV mirror. Live POST only if MKM_PET_BRIDGE_ENABLE_LIVE_POST=1.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipFortuneRegenerate,
    [switch]$PostBridgeDryRun,
    [switch]$SkipKvMirror,
    [switch]$SkipLiveSmoke,
    [switch]$NoDefaultDryRun,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$dotenv = Join-Path $WorkspaceRoot "scripts\Import-WorkspaceDotEnv_v1.ps1"
if (Test-Path -LiteralPath $dotenv) {
    . $dotenv -WorkspaceRoot $WorkspaceRoot
}

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

if (-not $SkipFortuneRegenerate) {
    Write-Host "[rq027] build_commander_daily_fortune_v1.py --skip-regenerate" -ForegroundColor Cyan
    & $py scripts/build_commander_daily_fortune_v1.py --skip-regenerate
    if ($LASTEXITCODE -ne 0 -and $Strict) { throw "fortune exit $LASTEXITCODE" }
}

Write-Host "[rq027] build_commander_dev_day_pack_v1.py" -ForegroundColor Cyan
& $py scripts/build_commander_dev_day_pack_v1.py
if ($LASTEXITCODE -ne 0) { throw "dev pack exit $LASTEXITCODE" }

Write-Host "[rq027] sync_commander_dev_pack_trust_packet_v2_v1.py" -ForegroundColor Cyan
& $py scripts/sync_commander_dev_pack_trust_packet_v2_v1.py
if ($LASTEXITCODE -ne 0) { throw "trust sync exit $LASTEXITCODE" }

Write-Host "[rq027] build_commander_dev_pack_pet_bridge_kv_stub_v1.py" -ForegroundColor Cyan
& $py scripts/build_commander_dev_pack_pet_bridge_kv_stub_v1.py
if ($LASTEXITCODE -ne 0) {
    if ($Strict) { throw "pet stub exit $LASTEXITCODE" }
    Write-Warning "pet stub integrity check failed — see stub JSON"
}

$doDryRun = $PostBridgeDryRun -or (-not $NoDefaultDryRun)
if ($doDryRun) {
    $stub = Join-Path $WorkspaceRoot "reports\commander_dev_pack_pet_bridge_kv_stub_latest.json"
    if (Test-Path -LiteralPath $stub) {
        Write-Host "[rq027] fetch_pet_companion_device_bridge_live_v1.py --dry-run" -ForegroundColor Cyan
        & $py scripts/fetch_pet_companion_device_bridge_live_v1.py --dry-run `
            --request-out (Join-Path $WorkspaceRoot "reports\tmp\commander_dev_pack_pet_bridge_request_dry_run_latest.json")
        if ($LASTEXITCODE -ne 0 -and $Strict) { throw "bridge dry-run exit $LASTEXITCODE" }
    }
}

if (-not $SkipKvMirror) {
    Write-Host "[rq027] write_commander_dev_pack_pet_kv_mirror_v1.py" -ForegroundColor Cyan
    & $py scripts/write_commander_dev_pack_pet_kv_mirror_v1.py
    if ($LASTEXITCODE -ne 0 -and $Strict) { throw "kv mirror exit $LASTEXITCODE" }
    if ($env:MKM_PET_KV_REMOTE_WRITE -match '^(1|true|yes|on)$') {
        Write-Host "[rq027] build_pet_companion_memory_slots_v1.py (KV refresh)" -ForegroundColor Cyan
        & $py scripts/build_pet_companion_memory_slots_v1.py
        if ($LASTEXITCODE -ne 0 -and $Strict) { Write-Warning "memory slots refresh exit $LASTEXITCODE" }
    }
}

if (-not $SkipLiveSmoke) {
    Write-Host "[rq027] run_commander_dev_pack_pet_bridge_live_smoke_v1.py" -ForegroundColor Cyan
    & $py scripts/run_commander_dev_pack_pet_bridge_live_smoke_v1.py
    if ($LASTEXITCODE -ne 0 -and $Strict) { throw "live smoke exit $LASTEXITCODE" }
}

Write-Host "[rq027] OK" -ForegroundColor Green
exit 0
