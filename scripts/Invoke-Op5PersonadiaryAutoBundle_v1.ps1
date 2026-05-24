#Requires -Version 5.1
<#
.SYNOPSIS
  O-P5 + personadiary draft + MS paste readiness + 상용화 병렬 (지휘관 SSH는 warn-only).
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $root) { $root = "c:\workspace" }
Set-Location $root

$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "py" }

$warn = @()

function Step-Ok {
    param([string]$Name, [scriptblock]$Block, [switch]$WarnOnly)
    Write-Host "== $Name ==" -ForegroundColor Cyan
    & $Block
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        if ($WarnOnly) {
            Write-Host "WARN $Name exit=$code (continuing)" -ForegroundColor Yellow
            $script:warn += "$Name exit=$code"
            return
        }
        Write-Host "FAIL $Name exit=$code" -ForegroundColor Red
        exit $code
    }
    Write-Host "OK $Name" -ForegroundColor Green
}

Step-Ok "personadiary_v6_draft" { & $py scripts/build_personadiary_logos_oracle_sphere_v6_draft_v1.py }

Step-Ok "op5_cf_jema12_apply" -WarnOnly {
    & $py scripts/setup_cloudflare_jema12_studio_oracle_redirect_v1.py
}

Step-Ok "op5_verify_jema12" -WarnOnly {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_jema12_studio_oracle_redirect_v1.ps1
}

Step-Ok "ms_paste_readiness" {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MsRq019PastePackReadiness_v1.ps1
}

Step-Ok "final_parallel_ops" {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MkmFinalParallelOps_v1.ps1 -SkipMsPasteWarn
}

Step-Ok "b2b_meeting_pack" {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-TrackCB2bMeetingPack_v1.ps1
}

Step-Ok "track_a_daily" {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_track_a_commercialization_daily_chain.ps1 -GateMode warning
}

Step-Ok "logos_commercial_bundle" {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LogosObservatoryCommercializationBundle_v1.ps1
}

Step-Ok "personadiary_cf_readiness" -WarnOnly {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-PersonadiaryCloudflareRoutingReadiness_v1.ps1
}

$summary = @{
    schema = "op5_personadiary_auto_bundle_v1"
    completed_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    warnings = $warn
    artifacts = @(
        "reports/personadiary/logos_oracle_sphere_v6_sync_draft.html",
        "reports/personadiary/logos_oracle_sphere_v6_sync_draft_latest.json",
        "reports/cloudflare_jema12_studio_oracle_redirect_latest.json",
        "reports/jema12_studio_oracle_redirect_check_latest.json"
    )
}
$outJson = Join-Path $root "reports/op5_personadiary_auto_bundle_latest.json"
New-Item -ItemType Directory -Force -Path (Split-Path $outJson) | Out-Null
$summary | ConvertTo-Json -Depth 6 | Set-Content -Path $outJson -Encoding UTF8

if ($warn.Count -gt 0) {
    Write-Host "DONE with warnings: $($warn -join '; ')" -ForegroundColor Yellow
    exit 0
}
Write-Host "O-P5 + personadiary auto bundle complete (exit 0)." -ForegroundColor Green
exit 0
