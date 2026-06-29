#Requires -Version 5.1
# Deploy jemaai-robots-v1 worker route via wrangler OAuth (needs workers_routes:write).
param(
    [string]$WorkerDir = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp\workers\jemaai-robots-v1"
)

$ErrorActionPreference = "Stop"
foreach ($k in @("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN", "CLOUDFLARE_RULESETS_API_TOKEN")) {
    Remove-Item "Env:$k" -ErrorAction SilentlyContinue
}
Set-Location -LiteralPath $WorkerDir
Write-Host "[jemaai-robots] wrangler deploy (OAuth)" -ForegroundColor Cyan
npx wrangler deploy
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "[jemaai-robots] route jemaai.cloud/robots.txt deployed" -ForegroundColor Green
exit 0
