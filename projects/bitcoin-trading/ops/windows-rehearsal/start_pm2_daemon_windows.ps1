$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$ecosystemFile = Join-Path $projectRoot "ecosystem.windows.config.js"
$env:PM2_HOME = Join-Path $projectRoot ".pm2-win"

if (-not (Test-Path $ecosystemFile)) {
    throw "Missing ecosystem config: $ecosystemFile"
}

Set-Location $projectRoot
if (-not (Test-Path $env:PM2_HOME)) {
    New-Item -ItemType Directory -Path $env:PM2_HOME | Out-Null
}

Write-Host "[Preflight] PM2_HOME=$env:PM2_HOME"
pm2 ping | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw @"
PM2 daemon handshake failed.
Likely cause in this environment: Node.js v24 compatibility/pipe permission issue.
Recommended fix:
1) Install Node.js 22 LTS
2) Reinstall PM2 globally: npm i -g pm2 pm2-windows-startup
3) Re-run this script
"@
}

Write-Host "[1/4] Starting PM2 daemon config..."
pm2 start $ecosystemFile --only bitcoin-trading-daemon-win

Write-Host "[2/4] Saving PM2 process list..."
pm2 save

Write-Host "[3/4] Status check..."
pm2 status

Write-Host "[4/4] Reminder: install startup once per machine:"
Write-Host "    npm install -g pm2 pm2-windows-startup"
Write-Host "    pm2-startup install"
