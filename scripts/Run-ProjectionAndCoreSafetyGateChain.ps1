<#
.SYNOPSIS
  Single entry: Dimensional Projection gates + Core Safety shadow promotion/rollback chain.

.DESCRIPTION
  Phase A (optional): full holdout validation + optional freeze promotion to active.
  Phase B (default): DP alert check on latest holdout eval report.
  Phase C (default): core-safety shadow compare -> decision -> proposal -> stability gate -> auto-rollback.

  Does NOT apply shadow promotion with --confirm (human gate remains in apply_core_safety_shadow_promotion_v1.py).

.PARAMETER WorkspaceRoot
  Repo root (default: parent of scripts/).

.PARAMETER RunHoldoutValidation
  Run scripts/Run-DimensionalProjectionHoldoutValidation.ps1 (long-running; embeddings optional).

.PARAMETER PromoteFreezeIfGatePass
  After holdout, run Promote-DimensionalProjectionFreeze.ps1 if holdout_gate_latest.json has overall_pass=true.

.PARAMETER FailOnDimensionalAlert
  Exit non-zero when check_dimensional_projection_alert_v1 reports alerting=true.

.PARAMETER ShadowCompareOnly
  Skip holdout and alert; only run core-safety shadow chain (steps 3-6).

.PARAMETER RequireCoreSafetyShadow
  If the default run12 core-safety evalset JSONL is missing, exit non-zero. Default: skip shadow sub-chain with a logged reason.

.PARAMETER ReportJsonForAlert
  Override --report-json for alert check (default: holdout multi-policy report path).
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [switch]$RunHoldoutValidation,
    [switch]$PromoteFreezeIfGatePass,
    [switch]$FailOnDimensionalAlert,
    [switch]$ShadowCompareOnly,
    [switch]$RequireCoreSafetyShadow,
    [string]$ReportJsonForAlert = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
$root = $WorkspaceRoot
$apiScripts = Join-Path $root "api-services\scripts"
$reports = Join-Path $root "reports\dimensional_projection_bridge"
$summaryPath = Join-Path $reports "projection_core_safety_chain_latest.json"

$steps = [System.Collections.ArrayList]@()

function Add-Step([string]$name, [int]$exitCode, [string]$note = "") {
    [void]$steps.Add([ordered]@{ name = $name; exit_code = $exitCode; note = $note; ts_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") })
}

function Write-Summary([int]$overallExit) {
    New-Item -ItemType Directory -Path $reports -Force | Out-Null
    $obj = [ordered]@{
        schema          = "projection_core_safety_chain_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        workspace_root  = $root
        overall_exit_code = $overallExit
        steps           = @($steps)
    }
    $obj | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding utf8
    Write-Host "Chain summary: $summaryPath" -ForegroundColor Green
}

Push-Location $root
$exitOverall = 0
try {

    if ($RunHoldoutValidation) {
        $hv = Join-Path $root "scripts\Run-DimensionalProjectionHoldoutValidation.ps1"
        if (-not (Test-Path -LiteralPath $hv)) { throw "Missing $hv" }
        Write-Host "==> Phase A1: Dimensional projection holdout validation" -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File $hv -WorkspaceRoot $root
        $e = $LASTEXITCODE
        Add-Step "holdout_validation" $e
        if ($e -ne 0) { $exitOverall = $e; throw "Holdout validation failed (exit $e)" }

        if ($PromoteFreezeIfGatePass) {
            $gatePath = Join-Path $reports "holdout_gate_latest.json"
            if (-not (Test-Path -LiteralPath $gatePath)) {
                Add-Step "promote_freeze_skipped" 0 "missing_holdout_gate_json"
            } else {
                $gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
                if (-not [bool]$gate.overall_pass) {
                    Add-Step "promote_freeze_skipped" 0 "overall_pass_false"
                } else {
                    $pr = Join-Path $root "scripts\Promote-DimensionalProjectionFreeze.ps1"
                    Write-Host "==> Phase A2: Promote freeze -> active" -ForegroundColor Cyan
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $pr -WorkspaceRoot $root
                    $e2 = $LASTEXITCODE
                    Add-Step "promote_dimensional_projection_freeze" $e2
                    if ($e2 -ne 0) { $exitOverall = $e2; throw "Freeze promotion failed (exit $e2)" }
                }
            }
        }
    }

    if (-not $ShadowCompareOnly) {
        $alertPy = Join-Path $apiScripts "check_dimensional_projection_alert_v1.py"
        if (-not (Test-Path -LiteralPath $alertPy)) { throw "Missing $alertPy" }
        $rep = if (-not [string]::IsNullOrWhiteSpace($ReportJsonForAlert)) {
            $ReportJsonForAlert
        } else {
            Join-Path $reports "engine_eval_multi_policy_holdout_latest.json"
        }
        Write-Host "==> Phase B: DP alert check (report=$rep)" -ForegroundColor Cyan
        $failArg = @()
        if ($FailOnDimensionalAlert) { $failArg = @("--fail-on-alert") }
        py $alertPy --report-json $rep @failArg
        $eb = $LASTEXITCODE
        Add-Step "dimensional_projection_alert_check" $eb
        if ($eb -ne 0) { $exitOverall = $eb }
    }

    function Invoke-ApiPy([string]$ScriptName, [string[]]$Extra = @()) {
        $p = Join-Path $apiScripts $ScriptName
        if (-not (Test-Path -LiteralPath $p)) { throw "Missing $p" }
        & py $p @Extra
        return $LASTEXITCODE
    }

    $coreEvalset = Join-Path $reports "dimensional_projection_evalset_core_safety_block_hardened_run12.jsonl"
    $runShadow = $true
    if (-not (Test-Path -LiteralPath $coreEvalset)) {
        $msg = "missing_evalset:$coreEvalset"
        if ($ShadowCompareOnly -or $RequireCoreSafetyShadow) {
            Add-Step "core_safety_shadow_chain" 1 $msg
            $exitOverall = 1
            throw "Core safety shadow evalset not found. Build run12 evalset or drop -ShadowCompareOnly / -RequireCoreSafetyShadow."
        }
        Write-Warning "Skipping core-safety shadow sub-chain (evalset not present). $msg"
        Add-Step "core_safety_shadow_chain" 0 "skipped_$msg"
        $runShadow = $false
    }

    if ($runShadow) {
        Write-Host "==> Phase C1: Core safety shadow compare" -ForegroundColor Cyan
        $e1 = Invoke-ApiPy "run_core_safety_shadow_compare_run12_v1.py"
        Add-Step "core_safety_shadow_compare" $e1
        if ($e1 -ne 0) { $exitOverall = $e1; throw "Shadow compare failed (exit $e1)" }

        Write-Host "==> Phase C2: Shadow promotion decision" -ForegroundColor Cyan
        $e2 = Invoke-ApiPy "decide_core_safety_shadow_promotion_v1.py"
        Add-Step "decide_core_safety_shadow_promotion" $e2
        if ($e2 -ne 0) { $exitOverall = $e2; throw "Decision step failed (exit $e2)" }

        Write-Host "==> Phase C3: Build promotion proposal (manual approval gate)" -ForegroundColor Cyan
        $e3 = Invoke-ApiPy "build_core_safety_shadow_promotion_proposal_v1.py"
        Add-Step "build_core_safety_shadow_promotion_proposal" $e3
        if ($e3 -ne 0) { $exitOverall = $e3; throw "Proposal build failed (exit $e3)" }

        Write-Host "==> Phase C4: Stability gate" -ForegroundColor Cyan
        $e4 = Invoke-ApiPy "evaluate_core_safety_stability_gate_v1.py"
        Add-Step "evaluate_core_safety_stability_gate" $e4
        if ($e4 -ne 0) { $exitOverall = $e4; throw "Stability gate failed (exit $e4)" }

        Write-Host "==> Phase C5: Auto-rollback (if stability alert)" -ForegroundColor Cyan
        $e5 = Invoke-ApiPy "auto_rollback_core_safety_shadow_v1.py"
        Add-Step "auto_rollback_core_safety_shadow" $e5
        if ($e5 -ne 0) { $exitOverall = $e5; throw "Auto rollback step failed (exit $e5)" }
    }

    Write-Summary -overallExit $exitOverall
    exit $exitOverall
}
catch {
    Write-Summary -overallExit $(if ($exitOverall -ne 0) { $exitOverall } else { 1 })
    throw
}
finally {
    Pop-Location
}
