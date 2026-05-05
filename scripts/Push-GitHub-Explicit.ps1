#Requires -Version 5.1
<#
.SYNOPSIS
  Perform an explicit one-time push to GitHub (manual safety gate).

.DESCRIPTION
  Uses an explicit GitHub SSH URL, bypassing remotes with no_push sentinel.
  This script is intentionally strict so GitHub publication is always deliberate.

.EXAMPLE
  pwsh -NoProfile -File scripts/Push-GitHub-Explicit.ps1 `
    -Branch fix/my-branch `
    -GitHubRepo git@github.com:mkmlab-v2/mkm-destiny-ai-41e38ec6.git `
    -Acknowledge
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Branch,

    [Parameter(Mandatory = $true)]
    [string]$GitHubRepo,

    [switch]$SetUpstream,
    [switch]$Acknowledge
)

$ErrorActionPreference = "Stop"

if (-not $Acknowledge) {
    throw "Refusing to push to GitHub without -Acknowledge."
}
if ($GitHubRepo -notmatch "github\.com[:/]") {
    throw "GitHubRepo must be a github.com SSH/HTTPS URL."
}

Set-Location "C:\workspace"

$current = (git rev-parse --abbrev-ref HEAD).Trim()
if (-not $current) { throw "Could not determine current branch." }
if ($current -ne $Branch) {
    throw "Current branch '$current' does not match requested -Branch '$Branch'."
}

Write-Host "[INFO] Explicit GitHub push requested." -ForegroundColor Yellow
Write-Host "[INFO] Branch: $Branch"
Write-Host "[INFO] Repo:   $GitHubRepo"

if ($SetUpstream) {
    git push -u $GitHubRepo $Branch
} else {
    git push $GitHubRepo $Branch
}
if ($LASTEXITCODE -ne 0) {
    throw "GitHub push failed (exit $LASTEXITCODE)."
}

Write-Host "[DONE] Explicit GitHub push completed." -ForegroundColor Green
