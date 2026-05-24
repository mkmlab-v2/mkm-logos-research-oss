#Requires -Version 5.1
<#
.SYNOPSIS
  jemaai.cloud CF edge — triage → (optional) child token → secret apply → check → apply → autoverify.
  Recurrence guard: never overwrite CLOUDFLARE_API_TOKEN; never say "create new token daily".
#>
param([string]$WorkspaceRoot = "C:\workspace")

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

Write-Host "==> CF token roles triage" -ForegroundColor Cyan
py scripts/check_cloudflare_token_roles_v1.py
$triageExit = $LASTEXITCODE
if ($triageExit -eq 0) {
    Write-Host "[cf-oneshot] rulesets role OK — apply + autoverify" -ForegroundColor Green
    py scripts/apply_jemaai_cloud_showroom_cf_edge_rules_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-JemaaiShowroomEdgeAutoverify_v1.ps1 -SkipApply -SkipVpsSync
    exit $LASTEXITCODE
}

if ($triageExit -eq 2) {
    $secret = Join-Path $WorkspaceRoot "reports\cloudflare_jemaai_solo_edge_token_secret_LOCAL.json"
    if (Test-Path -LiteralPath $secret) {
        Write-Host "==> secret apply (RULESETS key only)" -ForegroundColor Cyan
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ApplyJemaaiShowroomCfEdgeTokenFromSecret_v1.ps1
        exit $LASTEXITCODE
    }
    Write-Host "==> try child token (parent needs User API Tokens Write)" -ForegroundColor Cyan
    py scripts/try_create_cloudflare_jemaai_solo_edge_token_v1.py
    if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $secret)) {
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ApplyJemaaiShowroomCfEdgeTokenFromSecret_v1.ps1
        exit $LASTEXITCODE
    }
    Write-Host "[cf-oneshot] BLOCKED: scope mismatch — edit EXISTING token in CF UI (recommended) OR paste secret JSON" -ForegroundColor Yellow
    Write-Host "  docs/final/JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md" -ForegroundColor Yellow
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Open-JemaaiShowroomCfEdgeTokenTemplate_v1.ps1
    exit 2
}

exit $triageExit
