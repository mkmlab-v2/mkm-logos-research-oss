<#
.SYNOPSIS
  logos.jema-ai.com one-shot: token create → CF DNS UI → CNAME API → VPS SSL nginx → smoke.

.NOTES
  Parent token lacks DNS Edit → opens CF DNS records UI (Tier 3). Polls DNS up to 3 min.
  SSL uses existing *.jema-ai.com wildcard cert (no certbot).
  SSH uses MkmVpsRemoteCommon (key + BatchMode + ConnectTimeout) — prevents 4h hang on password prompt.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$DnsPollSeconds = 180,
    [switch]$SkipOpenBrowser,
    [switch]$ForceSslNginx
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot
. (Join-Path $PSScriptRoot "MkmVpsRemoteCommon_v1.ps1")

$secret = Join-Path $root "reports\cloudflare_jema_ai_logos_dns_token_secret_LOCAL.json"
$dnsViaApi = $false

Write-Host "[logos-auto] try create DNS token" -ForegroundColor Cyan
& py (Join-Path $root "scripts\try_create_cloudflare_jema_ai_dns_token_v1.py")
$tokCreated = ($LASTEXITCODE -eq 0)

if ($tokCreated -and (Test-Path -LiteralPath $secret)) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Invoke-ApplyJemaAiLogosDnsTokenFromSecret_v1.ps1") -SecretJson $secret
    if ($LASTEXITCODE -eq 0) { $dnsViaApi = $true }
}

if (-not $dnsViaApi) {
    if (-not $SkipOpenBrowser) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Open-JemaAiLogosDnsTokenTemplate_v1.ps1") -OpenDnsRecords
    }
    Write-Host "[logos-auto] polling DNS logos.jema-ai.com (max ${DnsPollSeconds}s)" -ForegroundColor Cyan
    $deadline = (Get-Date).AddSeconds($DnsPollSeconds)
    $dnsOk = $false
    while ((Get-Date) -lt $deadline) {
        & py (Join-Path $root "scripts\check_logos_jema_ai_infra_readiness_v1.py") 2>$null
        $repPath = Join-Path $root "reports\logos_jema_ai_infra_readiness_latest.json"
        if (Test-Path -LiteralPath $repPath) {
            $rep = Get-Content -LiteralPath $repPath -Raw | ConvertFrom-Json
            if ($rep.dns_resolves) {
                $dnsOk = $true
                break
            }
        }
        Start-Sleep -Seconds 10
    }
    if (-not $dnsOk) {
        Write-Host "[logos-auto] DNS not live yet — add CNAME logos -> app.jema-ai.com in CF, then re-run" -ForegroundColor Yellow
        exit 2
    }
    if ((Test-Path -LiteralPath $secret) -and -not $dnsViaApi) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Invoke-ApplyJemaAiLogosDnsTokenFromSecret_v1.ps1") -SecretJson $secret
    }
}

$skipNginx = $false
if (-not $ForceSslNginx) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\verify_logos_jema_ai_deploy_v1.ps1")
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[logos-auto] SKIP VPS nginx — deploy verify already OK (use -ForceSslNginx to re-apply)" -ForegroundColor Green
        $skipNginx = $true
    }
}

if (-not $skipNginx) {
    $t = Get-MkmVpsRemoteTarget
    Write-Host "[logos-auto] VPS SSL nginx (wildcard *.jema-ai.com) host=$($t.HostName)" -ForegroundColor Cyan
    $vpsRepo = "/opt/mkm-destiny-ai-41e38ec6"
    $nginxExample = Join-Path $root "scripts\deploy\linux\nginx-logos-jema-ai-com.conf.example"
    $nginxApply = Join-Path $root "scripts\deploy\linux\apply_logos_jema_ai_nginx_v1.sh"
    Invoke-MkmVpsScp -LocalPath $nginxExample -RemoteSpec ("{0}:{1}/scripts/deploy/linux/" -f $t.Remote, $vpsRepo)
    Invoke-MkmVpsScp -LocalPath $nginxApply -RemoteSpec ("{0}:{1}/scripts/deploy/linux/" -f $t.Remote, $vpsRepo)
    Invoke-MkmVpsSsh -RemoteCommand "chmod +x $vpsRepo/scripts/deploy/linux/apply_logos_jema_ai_nginx_v1.sh && bash $vpsRepo/scripts/deploy/linux/apply_logos_jema_ai_nginx_v1.sh -y"
    Start-Sleep -Seconds 3
}

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\verify_logos_jema_ai_deploy_v1.ps1")
exit $LASTEXITCODE
