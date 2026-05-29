#Requires -Version 5.1
param(
    [Parameter(Mandatory = $true)]
    [string]$Message,
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
Set-Location $root
& git add -A
$staged = git diff --cached --name-only
if (-not $staged) {
    Write-Host "[commit-push] nothing staged"
    exit 0
}
& git commit -m $Message
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not $SkipPush) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\push-internal.ps1")
}
Write-Host "[commit-push] done"
