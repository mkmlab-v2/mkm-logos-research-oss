<#
.SYNOPSIS
  Weekly Oracle module lane observability — narrative/closure + Tier-2 prep (tier_0, no cap bump).

.NOTES
  [HYPO] B-track only. Does NOT run bloom cap chains or mkmlife deploy.
#>
$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
$reportPath = Join-Path $workspaceRoot "reports\mkm_oracle_module_observability_weekly_v1_latest.json"
Push-Location $workspaceRoot
try {
    $started = (Get-Date).ToUniversalTime().ToString("o")
    $steps = @()

    function Add-Step {
        param([string]$Name, [int]$Code)
        $script:steps += [ordered]@{ step = $Name; exit_code = $Code; ok = ($Code -eq 0) }
        if ($Code -ne 0) { throw "FAIL: $Name exit $Code" }
    }

    & py scripts/run_logos_oracle_post_tier3_passive_ops_chain_v1.py --skip-pytest
    Add-Step "post_tier3_passive_ops_chain" ($LASTEXITCODE)

    & py scripts/build_mkm_oracle_module_scheduler_coexistence_v1.py
    Add-Step "scheduler_coexistence" ($LASTEXITCODE)

    $payload = [ordered]@{
        schema           = "mkm_oracle_module_observability_weekly_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        started_at_utc   = $started
        research_only    = $true
        send_gate        = "HOLD"
        chain_pass       = $true
        steps            = $steps
        repro            = "powershell -File scripts\Invoke-MkmOracleModuleObservabilityWeeklyRoutine_v1.ps1"
    }
    $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding utf8
    Write-Host "OK: oracle module weekly routine -> $reportPath"
    exit 0
}
finally {
    Pop-Location
}
