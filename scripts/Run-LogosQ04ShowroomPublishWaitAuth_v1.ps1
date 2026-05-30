# Wait for mkmlife deploy CF token (secret JSON or .env), then publish q04.
param(
    [int]$MaxWaitMinutes = 8,
    [int]$PollSeconds = 20
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
$attempt = 0
Write-Host "[q04-auth-wait] polling deploy token up to $MaxWaitMinutes min (every ${PollSeconds}s)" -ForegroundColor Cyan
Write-Host "  Paste token -> reports\cloudflare_mkmlife_deploy_token_secret_LOCAL.json" -ForegroundColor DarkGray
Write-Host "  Or run: scripts\Open-MkmlifeCloudflareDeployTokenTemplate_v1.ps1" -ForegroundColor DarkGray

while ((Get-Date) -lt $deadline) {
    $attempt++
    $probe = & py scripts\_probe_cf_mkmlife_deploy_token_v1.py 2>&1
    Write-Host "[probe $attempt] $probe"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[q04-auth-wait] deploy token OK — publishing" -ForegroundColor Green
        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosQ04ShowroomPublish_v1.ps1 -SkipBuild
        exit $LASTEXITCODE
    }
    Start-Sleep -Seconds $PollSeconds
}

Write-Host "[FAIL] deploy token not ready after $MaxWaitMinutes min" -ForegroundColor Red
Write-Host "Required: Workers Scripts Edit + Workers KV Storage Edit on account 646e42cf..." -ForegroundColor Yellow
exit 1
