#Requires -Version 5.1
<#
.SYNOPSIS
  If remote refs/heads/main and refs/heads/dev point at the same SHA, delete refs/heads/dev.

.DESCRIPTION
  Bare/internal workflows sometimes recreate a tracking dev ref identical to main.
  This script is safe to run repeatedly: it no-ops unless both heads exist and match.

.NOTES
  Exit 0 always unless git errors. Deletes only when SHA equality is confirmed.
#>
param(
    [string]$Remote = "gitea",
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$repoRoot = "C:\workspace"
if ($env:MKM_WORKSPACE_ROOT) {
    $repoRoot = $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
}
Set-Location $repoRoot

$remoteUrl = (git remote get-url $Remote 2>$null)
if (-not $remoteUrl) {
    Write-Host "[SKIP] No git remote named '$Remote'." -ForegroundColor DarkGray
    exit 0
}

git fetch $Remote --prune 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Warning "git fetch $Remote --prune failed (exit $LASTEXITCODE); skip redundant dev prune."
    exit 0
}

$lines = @(git ls-remote $Remote "refs/heads/main" "refs/heads/dev" 2>$null)
$byRef = @{}
foreach ($line in $lines) {
    $t = $line.ToString().Trim()
    if (-not $t) { continue }
    $parts = $t -split "\s+", 2
    if ($parts.Count -ge 2) {
        $byRef[$parts[1].Trim()] = $parts[0].Trim()
    }
}

$mainSha = $byRef["refs/heads/main"]
$devSha = $byRef["refs/heads/dev"]

if (-not $mainSha) {
    Write-Host "[SKIP] $Remote has no refs/heads/main." -ForegroundColor DarkGray
    exit 0
}
if (-not $devSha) {
    Write-Host "[OK] $Remote has no refs/heads/dev (nothing to prune)." -ForegroundColor DarkGreen
    exit 0
}
if ($mainSha -ne $devSha) {
    Write-Host "[SKIP] $Remote main ($($mainSha.Substring(0,12))) != dev ($($devSha.Substring(0,12))); not deleting dev." -ForegroundColor Yellow
    exit 0
}

Write-Host "[INFO] $Remote refs/heads/main and refs/heads/dev both at $mainSha — removing redundant dev." -ForegroundColor Cyan
if ($WhatIf) {
    Write-Host "[WhatIf] Would run: git push $Remote --delete dev" -ForegroundColor Magenta
    exit 0
}

git push $Remote --delete dev 2>&1 | ForEach-Object { $_ }
if ($LASTEXITCODE -ne 0) {
    Write-Warning "git push $Remote --delete dev failed (exit $LASTEXITCODE)."
    exit 0
}

git fetch $Remote --prune 2>&1 | Out-Null
Write-Host "[DONE] Removed redundant $Remote/dev (same SHA as main)." -ForegroundColor Green
exit 0
