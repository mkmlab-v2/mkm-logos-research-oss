#Requires -Version 5.1
<#
.SYNOPSIS
  Daily fusion: Oracle/evolution/SafeOps/watchdog + outer_lens RAG dryrun (+ optional polar hypo).

  Intentionally NEVER runs: promote_op28_headline_kpi, Security task re-enable,
  holdout threshold apply, MS paste/HWPX/readiness.

  SSOT: MISSION_LOG 「Oracle·진화」+ 「압축·문서」+ 「auto·Oracle·압축」
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipStreakTick,
    [switch]$SkipEvolutionHealth,
    [switch]$SkipSafeOps,
    [switch]$SkipWatchdog,
    [switch]$RunOuterLensCoordinator,
    [switch]$IncludePolarHypo,
    [string]$OutJson = "reports/mkm_daily_oracle_compression_fusion_routine_v1_latest.json"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $root

$py = "py"
$steps = [System.Collections.Generic.List[object]]::new()

function Add-Step {
    param([string]$Name, [int]$ExitCode, [string]$Note = $null)
    $steps.Add([ordered]@{
            name      = $Name
            exit_code = $ExitCode
            note      = $Note
        }) | Out-Null
    if ($ExitCode -ne 0) {
        throw "Step failed: $Name (exit $ExitCode)"
    }
}

$forbidden = @(
    "promote_op28_headline_kpi_v1",
    "SecurityIntegrityTask re-enable",
    "holdout_threshold_apply",
    "MS paste/HWPX/readiness"
)

if (-not $SkipStreakTick) {
    Write-Host "==> run_prophecy_strict_streak_tick_v1.py" -ForegroundColor Cyan
    & $py scripts/run_prophecy_strict_streak_tick_v1.py 2>&1 | Out-Host
    Add-Step "strict_streak_tick" $LASTEXITCODE
}
else {
    Add-Step "strict_streak_tick" 0 "skipped"
}

if (-not $SkipEvolutionHealth) {
    Write-Host "==> Invoke-EvolutionAllowlistAndHealth_v1.ps1" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-EvolutionAllowlistAndHealth_v1.ps1 -WorkspaceRoot $root
    Add-Step "evolution_allowlist_health" $LASTEXITCODE
}
else {
    Add-Step "evolution_allowlist_health" 0 "skipped"
}

if (-not $SkipSafeOps) {
    Write-Host "==> Invoke-SafeOpsSurfaceCheck.ps1" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-SafeOpsSurfaceCheck.ps1 `
        -AllowDisabledSecurityIntegrityTask
    Add-Step "safe_ops_surface" $LASTEXITCODE
}
else {
    Add-Step "safe_ops_surface" 0 "skipped"
}

if (-not $SkipWatchdog) {
    Write-Host "==> check_prophecy_evolution_watchdog_v1.py" -ForegroundColor Cyan
    & $py scripts/check_prophecy_evolution_watchdog_v1.py --workspace-root $root
    Add-Step "prophecy_evolution_watchdog" $LASTEXITCODE
}
else {
    Add-Step "prophecy_evolution_watchdog" 0 "skipped"
}

$outerArgs = @("scripts/run_outer_lens_rag_dryrun_gate_v1.py")
if ($RunOuterLensCoordinator) {
    $outerArgs += "--run-coordinator", "--run-logos-gate"
}
Write-Host "==> run_outer_lens_rag_dryrun_gate_v1.py" -ForegroundColor Cyan
& $py @outerArgs 2>&1 | Out-Host
Add-Step "outer_lens_rag_dryrun" $LASTEXITCODE

if ($IncludePolarHypo) {
    Write-Host "==> run_polar_coord_compression_hypo_v1.py [HYPO]" -ForegroundColor Cyan
    & $py scripts/run_polar_coord_compression_hypo_v1.py 2>&1 | Out-Host
    Add-Step "polar_coord_compression_hypo" $LASTEXITCODE "B-track research_only"
}

$summary = [ordered]@{
    schema           = "mkm_daily_oracle_compression_fusion_routine_v1"
    ts_utc           = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    hypothesis_tier  = "B"
    research_only    = $true
    ok               = $true
    forbidden_steps  = $forbidden
    steps            = $steps
    artifact_pointers = @{
        prophecy_gates     = "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json"
        streak_tick        = "reports/prophecy_strict_streak_tick_v1_latest.json"
        outer_lens_dryrun  = "docs/final/artifacts/outer_lens_rag_dryrun_gate_v1_latest.json"
        polar_hypo         = "reports/polar_coord_compression_hypo_v1_latest.json"
    }
}

$outPath = Join-Path $root $OutJson
$outDir = Split-Path -Parent $outPath
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8

Write-Host "[OK] Fusion routine complete -> $outPath" -ForegroundColor Green
exit 0
