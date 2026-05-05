#Requires -Version 5.1
param()

$ErrorActionPreference = "Stop"

$repoRoot = "C:\workspace"
$barePath = "E:\Git\repos\mkm-destiny-ai-41e38ec6.git"

if (-not (Test-Path -LiteralPath $barePath)) {
    git clone --bare $repoRoot $barePath
}

Set-Location $repoRoot
git remote remove internal 2>$null
git remote add internal $barePath
git remote -v

Write-Host "`n[DONE] internal remote is configured -> $barePath" -ForegroundColor Green
