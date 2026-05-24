#Requires -Version 5.1
<#
.SYNOPSIS
  Next lanes: MS paste bundle + jema12 verify + showroom VPS sync (no RefreshStaging) + CF check.
#>
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$report = Join-Path $root "reports\next_lanes_step2_v1_latest.json"
$lanes = @{}

$jobs = @(
    @{
        Name = "ms_paste_bundle"
        Script = {
            Set-Location $using:root
            py scripts/build_ms_rq019_paste_bundle_v1.py
            py scripts/build_ms_rq019_auto_status_v1.py
            exit $LASTEXITCODE
        }
    },
    @{
        Name = "jema12_verify"
        Script = {
            Set-Location $using:root
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_jema12_studio_oracle_redirect_v1.ps1
            exit $LASTEXITCODE
        }
    },
    @{
        Name = "showroom_vps_sync"
        Script = {
            Set-Location $using:root
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\sync_showroom_to_vps.ps1
            exit $LASTEXITCODE
        }
    },
    @{
        Name = "cf_check"
        Script = {
            Set-Location $using:root
            py scripts/check_jemaai_cloud_cf_rules_token_v1.py
            exit $LASTEXITCODE
        }
    }
)

Write-Host "== Step2 parallel: MS paste | jema12 | VPS sync | CF check ==" -ForegroundColor Cyan
foreach ($def in $jobs) {
    $j = Start-Job -Name $def.Name -ScriptBlock $def.Script
    Wait-Job -Job $j | Out-Null
    $out = Receive-Job -Job $j -ErrorAction SilentlyContinue
    $ok = ($j.State -eq "Completed")
    $lanes[$def.Name] = @{ ok = $ok; state = $j.State }
    Write-Host ""
    Write-Host "--- $($def.Name) ---" -ForegroundColor $(if ($ok) { "Green" } else { "Yellow" })
    if ($out) { $out | Select-Object -Last 12 | ForEach-Object { Write-Host $_ } }
    Remove-Job -Job $j -Force -ErrorAction SilentlyContinue
}

$failed = @($lanes.Keys | Where-Object { -not $lanes[$_].ok })
@{
    schema           = "next_lanes_step2_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    lanes            = $lanes
    failed           = $failed
    ok               = ($failed.Count -eq 0)
    ms_paste_bundle  = "reports/ms_rq019_paste_bundle_latest.md"
    ms_paste_dir     = "reports/ms_rq019_paste_ready/"
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $report -Encoding UTF8

Write-Host ""
Write-Host "Wrote $report ok=$($failed.Count -eq 0)" -ForegroundColor $(if ($failed.Count -eq 0) { "Green" } else { "Yellow" })
exit $(if ($failed.Count -eq 0) { 0 } else { 1 })
