<#
.SYNOPSIS
  Weekly mkmlife CF Workers vs jema-ai/logos VPS DNS/deploy axis isolation probe.

.NOTES
  [HYPO] B-track · research_only · send_gate HOLD — no mkmlife deploy · no Track A.
#>
$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
$reportPath = Join-Path $workspaceRoot "reports\mkm_deployment_axis_isolation_weekly_v1_latest.json"
Push-Location $workspaceRoot
try {
    $started = (Get-Date).ToUniversalTime().ToString("o")
    $steps = @()

    function Add-Step {
        param([string]$Name, [int]$Code)
        $script:steps += [ordered]@{ step = $Name; exit_code = $Code; ok = ($Code -eq 0) }
        if ($Code -ne 0) { throw "FAIL: $Name exit $Code" }
    }

    & py scripts/run_mkm_deployment_axis_isolation_chain_v1.py --profile core
    Add-Step "deployment_axis_isolation_chain" ($LASTEXITCODE)

    $payload = [ordered]@{
        schema           = "mkm_deployment_axis_isolation_weekly_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        started_at_utc   = $started
        research_only    = $true
        send_gate        = "HOLD"
        chain_pass       = $true
        steps            = $steps
        repro            = "powershell -File scripts\Invoke-MkmDeploymentAxisIsolationWeeklyRoutine_v1.ps1"
    }
    $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding utf8
    Write-Host "OK: deployment axis weekly routine -> $reportPath"
    exit 0
}
finally {
    Pop-Location
}
