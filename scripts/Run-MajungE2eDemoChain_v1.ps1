# Majung E2E demo chain: finance/macro input → offline macro API → forward health → demo bundle.
# Fact-Lock: artifacts + exit codes only; not a selection or trading performance claim.

param(
    [switch]$SkipFinanceInput,
    [switch]$SkipForwardHealth,
    [switch]$SkipP0,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$chainLog = Join-Path $repoRoot "reports\majung_e2e_demo_chain_steps_latest.json"
$steps = [System.Collections.Generic.List[object]]::new()

function Add-Step {
    param(
        [string]$Name,
        [int]$ExitCode,
        [string]$Note = ""
    )
    $steps.Add([ordered]@{
            name      = $Name
            exit_code = $ExitCode
            note      = $Note
            at_utc    = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        }) | Out-Null
}

function Invoke-DemoStep {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host ""
    Write-Host "[majung-e2e] === $Name ===" -ForegroundColor Cyan
    if ($WhatIfOnly) {
        Write-Host "[majung-e2e] WHATIF: would run $Name"
        Add-Step -Name $Name -ExitCode 0 -Note "whatif"
        return
    }
    try {
        & $Action
        $code = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
        Add-Step -Name $Name -ExitCode $code
        if ($code -ne 0) {
            throw "exit $code"
        }
    }
    catch {
        $code = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 1 }
        Add-Step -Name $Name -ExitCode $code -Note $_.Exception.Message
        throw
    }
}

Push-Location $repoRoot
try {
    if (-not $SkipFinanceInput) {
        Invoke-DemoStep -Name "build_finance_macro_b2b_compression_eval_input_v1" -Action {
            py scripts/build_finance_macro_b2b_compression_eval_input_v1.py
        }
        Invoke-DemoStep -Name "report_multilens_finance_macro_b2b" -Action {
            py scripts/report_multilens_performance_eval.py `
                --input docs/final/artifacts/finance_macro_b2b_compression_eval_input_v1.json `
                --output docs/final/artifacts/finance_macro_b2b_compression_active_report_v1.json `
                --mode experimental --strategy C --intensity high
        }
    }
    else {
        Add-Step -Name "build_finance_macro_b2b_compression_eval_input_v1" -ExitCode 0 -Note "skipped"
        Add-Step -Name "report_multilens_finance_macro_b2b" -ExitCode 0 -Note "skipped"
    }

    Invoke-DemoStep -Name "build_macro_risk_warning_api_offline_snapshot_v1" -Action {
        py scripts/build_macro_risk_warning_api_offline_snapshot_v1.py --include-evidence-ref
    }

    Invoke-DemoStep -Name "apply_macro_risk_decision_policy" -Action {
        py scripts/apply_macro_risk_decision_policy.py
    }

    if (-not $SkipForwardHealth) {
        $dash = Join-Path $repoRoot "docs\final\artifacts\mkm_trackc_ops_dashboard_latest.json"
        $fwdOut = Join-Path $repoRoot "docs\final\artifacts\macro_risk_forward_pipeline_health_gate_latest.json"
        if (Test-Path -LiteralPath $dash) {
            Invoke-DemoStep -Name "check_macro_risk_forward_pipeline_health_v1" -Action {
                py scripts/check_macro_risk_forward_pipeline_health_v1.py `
                    --dashboard-json $dash `
                    --output-json $fwdOut
            }
        }
        else {
            Write-Host "[majung-e2e] SKIP forward health (no dashboard JSON)" -ForegroundColor Yellow
            Add-Step -Name "check_macro_risk_forward_pipeline_health_v1" -ExitCode 0 -Note "skipped_no_dashboard"
        }
    }
    else {
        Add-Step -Name "check_macro_risk_forward_pipeline_health_v1" -ExitCode 0 -Note "skipped_flag"
    }

    if (-not $SkipP0) {
        Invoke-DemoStep -Name "verify_p0_constitution_gate_paths" -Action {
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_p0_constitution_gate_paths.ps1
        }
    }
    else {
        Add-Step -Name "verify_p0_constitution_gate_paths" -ExitCode 0 -Note "skipped_flag"
    }

    $logDir = Split-Path -Parent $chainLog
    if (-not (Test-Path -LiteralPath $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($chainLog, (@($steps) | ConvertTo-Json -Depth 6), $utf8NoBom)

    if (-not $WhatIfOnly) {
        Invoke-DemoStep -Name "build_majung_e2e_demo_report_v1" -Action {
            py scripts/build_majung_e2e_demo_report_v1.py --chain-log $chainLog
        }
    }

    Write-Host ""
    Write-Host "[majung-e2e] PASS — artifacts:" -ForegroundColor Green
    Write-Host "  docs/final/artifacts/majung_e2e_demo_latest.json"
    Write-Host "  docs/final/artifacts/majung_e2e_demo_latest.md"
    Write-Host "  docs/final/artifacts/macro_risk_warning_api_smoke_latest.json"
    Write-Host "  reports/majung_e2e_demo_chain_steps_latest.json"
}
finally {
    Pop-Location
}
