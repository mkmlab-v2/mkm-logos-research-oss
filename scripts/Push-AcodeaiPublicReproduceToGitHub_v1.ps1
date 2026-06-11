#Requires -Version 5.1
<#
.SYNOPSIS
  Push slim a-codeai public reproduce export to GitHub (explicit gate only).

.EXAMPLE
  pwsh -NoProfile -File scripts/Push-AcodeaiPublicReproduceToGitHub_v1.ps1 `
    -GitHubRepo git@github.com:mkmlab-v2/a-codeai-compression-reproduce.git `
    -Acknowledge

.EXAMPLE
  pwsh -NoProfile -File scripts/Push-AcodeaiPublicReproduceToGitHub_v1.ps1 `
    -RefreshMaterialize -VerifyChain -Acknowledge

.NOTES
  After materialize (or on existing export .git), dirty export tree is auto-committed before push.
#>
param(
    [string]$ExportDir = "exports/a-codeai-public-reproduce-v2",
    [string]$GitHubRepo = "git@github.com:mkmlab-v2/a-codeai-compression-reproduce.git",
    [string]$GitHubOwnerRepo = "mkmlab-v2/a-codeai-compression-reproduce",
    [switch]$RefreshMaterialize,
    [switch]$VerifyChain,
    [switch]$CreateRepoIfMissing,
    [switch]$Acknowledge
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
Set-Location $root

if (-not $Acknowledge) {
    throw "Refusing GitHub push without -Acknowledge (SEND_GATE HOLD — technical reproduce only)."
}
if ($GitHubRepo -notmatch "github\.com[:/]") {
    throw "GitHubRepo must be a github.com SSH/HTTPS URL."
}

$abs = Join-Path $root $ExportDir
if (-not (Test-Path $abs)) { throw "export dir missing: $abs" }

if ($RefreshMaterialize) {
    $matArgs = @("scripts/materialize_a_codeai_public_reproduce_bundle_v1.py", "--out-dir", $ExportDir)
    if ($VerifyChain) { $matArgs += "--verify-chain" }
    & py @matArgs
    if ($LASTEXITCODE -ne 0) { throw "materialize failed (exit $LASTEXITCODE)" }
}

Push-Location $abs
try {
    $exportGit = Join-Path (Get-Location).Path ".git"
    if (-not (Test-Path $exportGit)) {
        Write-Host "[INFO] initializing isolated git repo in export dir" -ForegroundColor Cyan
        git init -b main
        git add -A
        git commit -m "chore: a-codeai public reproduce export (SEND_GATE HOLD)"
        if ($LASTEXITCODE -ne 0) { throw "initial export commit failed (exit $LASTEXITCODE)" }
    }

    if ($CreateRepoIfMissing) {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        gh repo view $GitHubOwnerRepo 1>$null 2>$null
        $repoExists = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = $prevEap
        if (-not $repoExists) {
            Write-Host "[INFO] creating public repo $GitHubOwnerRepo" -ForegroundColor Cyan
            gh repo create $GitHubOwnerRepo --public `
                --description "A-CODEAI open-bench reproduce bundle (SEND_GATE HOLD · per-SKU metrics only)" `
                --source . --remote github
            if ($LASTEXITCODE -ne 0) { throw "gh repo create failed (exit $LASTEXITCODE)" }
        } elseif (-not (git remote get-url github 2>$null)) {
            git remote add github $GitHubRepo
        }
    } else {
        if (-not (git remote get-url github 2>$null)) {
            git remote add github $GitHubRepo
        }
    }

    git add -A
    $porcelain = git status --porcelain
    if ($porcelain) {
        $stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
        git commit -m "chore(open-bench): export refresh $stamp (SEND_GATE HOLD)"
        if ($LASTEXITCODE -ne 0) { throw "export commit failed (exit $LASTEXITCODE)" }
        Write-Host "[INFO] committed export changes before push" -ForegroundColor Cyan
    } else {
        Write-Host "[INFO] export tree clean — nothing to commit" -ForegroundColor DarkGray
    }

    git push -u github main
    if ($LASTEXITCODE -ne 0) { throw "git push github main failed (exit $LASTEXITCODE)" }

    Write-Host "[DONE] GitHub mirror push OK: $GitHubRepo (branch main)" -ForegroundColor Green
    Write-Host "[NOTE] SEND_GATE HOLD — not a customer case study or merged marketing headline." -ForegroundColor Yellow
}
finally {
    Pop-Location
}
