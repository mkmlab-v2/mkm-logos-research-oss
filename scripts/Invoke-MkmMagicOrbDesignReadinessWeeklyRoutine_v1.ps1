<#
.SYNOPSIS
  Weekly Magic Orb design readiness — Playwright screenshot + engineering merge.

.NOTES
  [HYPO] B-track · research_only · send_gate HOLD — no Track A · consumer_ready needs commander visual.
#>
$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
$reportPath = Join-Path $workspaceRoot "reports\magic_orb_design_readiness_weekly_v1_latest.json"
Push-Location $workspaceRoot
try {
    $started = (Get-Date).ToUniversalTime().ToString("o")
    $steps = @()

    function Add-Step {
        param([string]$Name, [int]$Code)
        $script:steps += [ordered]@{ step = $Name; exit_code = $Code; ok = ($Code -eq 0) }
        if ($Code -ne 0) { throw "FAIL: $Name exit $Code" }
    }

    & py scripts/run_magic_orb_design_readiness_chain_v1.py
    Add-Step "magic_orb_design_readiness_chain" ($LASTEXITCODE)

    $readinessPath = Join-Path $workspaceRoot "reports\magic_orb_design_readiness_v1_latest.json"
    $readiness = $null
    if (Test-Path -LiteralPath $readinessPath) {
        $readiness = Get-Content -LiteralPath $readinessPath -Raw -Encoding UTF8 | ConvertFrom-Json
    }

    $payload = [ordered]@{
        schema           = "magic_orb_design_readiness_weekly_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        started_at_utc   = $started
        research_only    = $true
        send_gate        = "HOLD"
        chain_pass       = $true
        engineering_ok   = $readiness.engineering_ok
        design_ok        = $readiness.design_ok
        consumer_ready   = $readiness.consumer_ready
        verdict_ko       = $readiness.verdict_ko
        steps            = $steps
        repro            = "powershell -File scripts\Invoke-MkmMagicOrbDesignReadinessWeeklyRoutine_v1.ps1"
    }
    $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding utf8
    Write-Host "OK: magic orb design readiness weekly -> $reportPath design_ok=$($readiness.design_ok)"
    exit 0
}
finally {
    Pop-Location
}
