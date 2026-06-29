#Requires -Version 5.1

<#

.SYNOPSIS

  Refresh artifacts for 08:28 prophecy Telegram (market briefs only by default).



.DESCRIPTION

  Best-effort before send_telegram_minimal_ops_digest_v1.py --style prophecy.

  Default: dual-leg + KOSPI onepager only (no fortune/dev/pet — prophecy TG blocks are off).

  Does not fail the morning send unless -Strict.

#>

param(

    [string]$WorkspaceRoot = "C:\workspace",

    [switch]$Strict,

    [switch]$IncludeDevPetChain

)



$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $WorkspaceRoot



$py = (Get-Command py -ErrorAction SilentlyContinue).Source

if (-not $py) { $py = "py" }

# P0 tier_0 — Field shock policy + morning brief before prophecy TG (P3 forbidden)
$p0Preflight = Join-Path $WorkspaceRoot "scripts\run_telegram_daily_p0_preflight_v1.py"
if (Test-Path -LiteralPath $p0Preflight) {
    Write-Host "[prophecy-refresh] run_telegram_daily_p0_preflight_v1.py (tier_0 Field wiring)" -ForegroundColor Cyan
    & $py $p0Preflight
    if ($LASTEXITCODE -ne 0) {
        if ($Strict) { throw "telegram daily P0 preflight exit $LASTEXITCODE" }
        Write-Warning "telegram P0 preflight failed; morning brief may be stale for Field Final Call"
    }
}

$juneLoop = Join-Path $WorkspaceRoot "scripts\Invoke-KospiJune2026ProphecyLoop_v1.ps1"
if (Test-Path -LiteralPath $juneLoop) {
    Write-Host "[prophecy-refresh] Invoke-KospiJune2026ProphecyLoop_v1.ps1 -Phase Morning" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $juneLoop -WorkspaceRoot $WorkspaceRoot -Phase Morning -YearMonth 2026-06
    if ($LASTEXITCODE -ne 0) {
        if ($Strict) { throw "KospiJune morning loop exit $LASTEXITCODE" }
        Write-Warning "KospiJune morning loop failed; calendar block may be stale"
    }
}

$scoreJson = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_prophecy_score_latest.json"

$briefPs1 = Join-Path $WorkspaceRoot "scripts\Invoke-ProphecyDualLegAndKospiBrief_v1.ps1"

if ((Test-Path -LiteralPath $scoreJson) -and (Test-Path -LiteralPath $briefPs1)) {

    Write-Host "[prophecy-refresh] Invoke-ProphecyDualLegAndKospiBrief_v1.ps1" -ForegroundColor Cyan

    & powershell -NoProfile -ExecutionPolicy Bypass -File $briefPs1 -WorkspaceRoot $WorkspaceRoot

    if ($LASTEXITCODE -ne 0) {

        if ($Strict) { throw "Invoke-ProphecyDualLegAndKospiBrief exit $LASTEXITCODE" }

        Write-Warning "dual-leg/kospi brief refresh failed; TG market block may be stale"

    }

} else {

    Write-Host "[prophecy-refresh] skip dual-leg brief (no score JSON or script)" -ForegroundColor DarkGray

}

$missionSummary = Join-Path $WorkspaceRoot "reports\mission_c_srcdir_expanded_shadow_summary_v1_latest.json"
if (Test-Path -LiteralPath $missionSummary) {
    Write-Host "[prophecy-refresh] build_mission_c_shadow_ops_status_v1.py (Mission C TG digest block)" -ForegroundColor DarkCyan
    & $py scripts/build_mission_c_shadow_ops_status_v1.py
    if ($LASTEXITCODE -ne 0) {
        if ($Strict) { throw "build_mission_c_shadow_ops_status exit $LASTEXITCODE" }
        Write-Warning "Mission C ops status refresh failed; TG shadow block may be stale"
    }
}

Write-Host "[prophecy-refresh] build_commander_daily_fortune_v1.py (사주·명리·일운)" -ForegroundColor Cyan
& $py scripts/build_commander_daily_fortune_v1.py --skip-regenerate
if ($LASTEXITCODE -ne 0) {
    if ($Strict) { throw "build_commander_daily_fortune exit $LASTEXITCODE" }
    Write-Warning "commander fortune refresh failed; personal block may be stale"
}

$wantDevPet = $IncludeDevPetChain
if (-not $wantDevPet) {
    $dp = [Environment]::GetEnvironmentVariable("MKM_TELEGRAM_PROPHECY_INCLUDE_DEV_COACH", "Process")
    if (-not $dp) { $dp = [Environment]::GetEnvironmentVariable("MKM_TELEGRAM_PROPHECY_INCLUDE_DEV_COACH", "User") }
    if ($dp -match '^(1|true|yes|on)$') { $wantDevPet = $true }
}

if ($wantDevPet) {
    Write-Host "[prophecy-refresh] Invoke-CommanderDevPackPetBridgeChain_v1.ps1 (dev+trust+pet stub)" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-CommanderDevPackPetBridgeChain_v1.ps1 `
        -WorkspaceRoot $WorkspaceRoot -SkipFortuneRegenerate
    if ($LASTEXITCODE -ne 0) {
        if ($Strict) { throw "RQ-027 dev pack chain exit $LASTEXITCODE" }
        Write-Warning "RQ-027 chain failed; dev coach / trust / pet stub may be stale"
    }
}

Write-Host "[prophecy-refresh] OK" -ForegroundColor Green
exit 0

