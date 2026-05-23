#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot: triage → try child token create → apply secret if present → smartfarm redirect → curl smoke.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipVpsNginx
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$report = @{
    schema = "cloudflare_jema_ai_redirect_auto_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    steps = @{}
}

Write-Host "== 1/5 token triage ==" -ForegroundColor Cyan
$prev = $ErrorActionPreference
$ErrorActionPreference = "Continue"
py scripts/check_cloudflare_token_roles_v1.py *> $null
$report.steps.triage = @{ exit_code = $LASTEXITCODE }
$ErrorActionPreference = $prev
$triagePath = Join-Path $WorkspaceRoot "reports\cloudflare_token_roles_triage_v1_latest.json"
$ready = $false
if (Test-Path $triagePath) {
    $t = Get-Content $triagePath -Raw | ConvertFrom-Json
    $ready = [bool]$t.jema_ai_dynamic_redirect.automation_ready
    $report.steps.triage.ready = $ready
}

if (-not $ready) {
    Write-Host "== 2/5 try create child token (parent API) ==" -ForegroundColor Cyan
    py scripts/try_create_cloudflare_jema_ai_redirect_token_v1.py 2>&1 | Out-Host
    $report.steps.try_create = @{ exit_code = $LASTEXITCODE }
    $secretPath = Join-Path $WorkspaceRoot "reports\cloudflare_jema_ai_redirect_token_secret_LOCAL.json"
    if (Test-Path $secretPath) {
        Write-Host "== 3/5 apply secret ==" -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-ApplyJemaAiRedirectTokenFromSecret_v1.ps1")
        $report.steps.apply_secret = @{ exit_code = $LASTEXITCODE }
        if ($LASTEXITCODE -eq 0) { $ready = $true }
    } else {
        $report.steps.apply_secret = @{ skipped = "no secret file" }
        Write-Host "[auto] CF scope still missing — dashboard 1-line fix required (see jema_ai_redirect_guard)" -ForegroundColor Yellow
    }
} else {
    Write-Host "== 2-3/5 skip create (already ready) ==" -ForegroundColor Green
}

if ($ready) {
    Write-Host "== 4/5 apply smartfarm redirect ==" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-CloudflareJemaAiSmartfarmRedirect_v1.ps1") -SkipTriage
    $report.steps.smartfarm_apply = @{ exit_code = $LASTEXITCODE }
} else {
    $report.steps.smartfarm_apply = @{ skipped = "jema_ai_dynamic_redirect not ready" }
}

if (-not $SkipVpsNginx) {
    Write-Host "== 5/5 VPS nginx apex (origin fallback) ==" -ForegroundColor Cyan
    $sshKey = $env:MKM_VPS_SSH_KEY_PATH
    if (-not $sshKey) { $sshKey = Join-Path $env:USERPROFILE ".ssh\hostinger_mkmlife" }
    $sshHost = if ($env:MKM_VPS_HOST) { $env:MKM_VPS_HOST } else { "srv1101456.hstgr.cloud" }
    $user = if ($env:MKM_VPS_USER) { $env:MKM_VPS_USER } else { "root" }
    if (Test-Path $sshKey) {
        $cmd = "cd /opt/mkm-destiny-ai-41e38ec6 && (git pull gitea main 2>/dev/null || git pull origin main 2>/dev/null || true); test -f scripts/deploy/linux/apply_jema_ai_com_apex_nginx_v1.sh && sudo bash scripts/deploy/linux/apply_jema_ai_com_apex_nginx_v1.sh -y || echo NGINX_SCRIPT_MISSING"
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        ssh -i $sshKey -o StrictHostKeyChecking=accept-new "${user}@${sshHost}" $cmd 2>&1 | Out-Host
        $report.steps.vps_nginx = @{ exit_code = $LASTEXITCODE; host = $sshHost }
        $ErrorActionPreference = $prevEap
    } else {
        $report.steps.vps_nginx = @{ skipped = "ssh key missing" }
    }
}

Write-Host "== curl smoke ==" -ForegroundColor Cyan
curl.exe -sSI "https://jema-ai.com/smartfarm" 2>&1 | Select-Object -First 6 | Out-Host
$outPath = Join-Path $WorkspaceRoot "reports\cloudflare_jema_ai_redirect_auto_v1_latest.json"
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "Wrote $outPath" -ForegroundColor Green
if ($ready) { exit 0 }
exit 2
