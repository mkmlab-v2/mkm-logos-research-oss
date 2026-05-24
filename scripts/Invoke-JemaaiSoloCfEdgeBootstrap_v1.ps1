#Requires -Version 5.1

<#

.SYNOPSIS

  1인 개발: CF rulesets token (RULESETS key only) -> apply -> autoverify.

.NOTES

  Recurrence guard: never overwrites CLOUDFLARE_API_TOKEN. Run triage first.

#>

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot

Set-Location $Root



Write-Host "[solo-cf] token roles triage..." -ForegroundColor Cyan

py scripts/check_cloudflare_token_roles_v1.py 2>&1 | Out-Host

if ($LASTEXITCODE -eq 0) {

    Write-Host "[solo-cf] rulesets token already ready." -ForegroundColor Green

} elseif ($LASTEXITCODE -eq 2) {

    Write-Host "[solo-cf] scope mismatch — try child token OR paste RULESETS secret (not new CLOUDFLARE_API_TOKEN)..." -ForegroundColor Cyan

    py scripts/try_create_cloudflare_jemaai_solo_edge_token_v1.py

    if ($LASTEXITCODE -eq 0) {

        $apply = Join-Path $Root "scripts\Invoke-ApplyJemaaiShowroomCfEdgeTokenFromSecret_v1.ps1"

        if (Test-Path -LiteralPath $apply) {

            powershell -NoProfile -ExecutionPolicy Bypass -File $apply

            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

        }

    } else {

        Write-Host "[solo-cf] Child token create failed. ONE-TIME: CF UI -> secret JSON -> Invoke-ApplyJemaaiShowroomCfEdgeTokenFromSecret_v1.ps1" -ForegroundColor Yellow

        Write-Host "  See: docs/final/JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md (section recurrence guard)" -ForegroundColor Yellow

        powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "scripts\Open-JemaaiShowroomCfEdgeTokenTemplate_v1.ps1")

        exit 2

    }

} else {

    Write-Host "[solo-cf] triage exit $LASTEXITCODE — fix tokens per reports/cloudflare_token_roles_triage_v1_latest.json" -ForegroundColor Yellow

    exit $LASTEXITCODE

}



py scripts/check_cloudflare_token_roles_v1.py 2>&1 | Out-Host

if ($LASTEXITCODE -ne 0) {

    Write-Host "[solo-cf] still not ready — Reload Cursor after User env sync." -ForegroundColor Yellow

    exit 2

}



Write-Host "[solo-cf] apply showroom edge rules..." -ForegroundColor Cyan

py scripts/apply_jemaai_cloud_showroom_cf_edge_rules_v1.py

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-JemaaiShowroomEdgeAutoverify_v1.ps1 -SkipApply

exit $LASTEXITCODE

