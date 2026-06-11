#Requires -Version 5.1
<#
.SYNOPSIS
  Materialize + verify public reproduce export, then init local git mirror for explicit GitHub push.

.EXAMPLE
  pwsh -NoProfile -File scripts/Init-AcodeaiPublicReproduceGitMirror_v1.ps1 -VerifyChain
#>
param(
    [string]$OutDir = "exports/a-codeai-public-reproduce-v1",
    [switch]$VerifyChain,
    [switch]$SkipMaterialize
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

if (-not $SkipMaterialize) {
    $matArgs = @("scripts/materialize_a_codeai_public_reproduce_bundle_v1.py", "--out-dir", $OutDir)
    if ($VerifyChain) { $matArgs += "--verify-chain" }
    & py @matArgs
    if ($LASTEXITCODE -ne 0) { throw "materialize failed (exit $LASTEXITCODE)" }
}

$abs = Join-Path (Get-Location) $OutDir
if (-not (Test-Path $abs)) { throw "export dir missing: $abs" }

Push-Location $abs
try {
    $workspaceRoot = (Resolve-Path "C:\workspace").Path
    if ((Get-Location).Path -eq $workspaceRoot) {
        throw "refusing git init in monorepo root — OutDir must be under exports/"
    }
    if (-not (Test-Path ".git")) {
        git init -b main
    }
    git add -A
    $status = git status --porcelain
    if ($status) {
        git commit -m "chore: a-codeai public reproduce export (SEND_GATE HOLD)"
    } else {
        Write-Host "[INFO] nothing to commit" -ForegroundColor Yellow
    }
    Write-Host "[OK] local mirror ready: $abs" -ForegroundColor Green
    Write-Host "[NEXT] explicit GitHub push (human gate):" -ForegroundColor Cyan
    Write-Host "  cd $abs"
    Write-Host "  git remote add github git@github.com:<org>/<public-reproduce-repo>.git"
    Write-Host "  git push -u github main"
    Write-Host "  (or from monorepo branch: scripts/Push-GitHub-Explicit.ps1 -Branch <branch> -GitHubRepo ... -Acknowledge)"
}
finally {
    Pop-Location
}
