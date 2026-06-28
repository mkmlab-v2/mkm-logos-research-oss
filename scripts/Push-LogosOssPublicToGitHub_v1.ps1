#Requires -Version 5.1
<#
.SYNOPSIS
  Push curated Logos Research OSS export to GitHub (explicit gate only).

.EXAMPLE
  pwsh -NoProfile -File scripts/Push-LogosOssPublicToGitHub_v1.ps1 `
    -RefreshMaterialize -VerifyChain -CreateRepoIfMissing -Acknowledge

.NOTES
  Export SSOT: docs/final/artifacts/logos_oss_public_export_manifest_v1.json
  Materialize: exports/mkm-logos-research-oss-v1/
  SEND_GATE HOLD for grants/contracts; oss_github_release OPEN per solo OSS policy.
#>
param(
    [string]$ExportDir = "exports/mkm-logos-research-oss-v1",
    [string]$GitHubRepo = "git@github.com:mkmlab-v2/mkm-logos-research-oss.git",
    [string]$GitHubOwnerRepo = "mkmlab-v2/mkm-logos-research-oss",
    [switch]$RefreshMaterialize,
    [switch]$VerifyChain,
    [switch]$CreateRepoIfMissing,
    [switch]$Acknowledge
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
Set-Location $root

if (-not $Acknowledge) {
    throw "Refusing GitHub push without -Acknowledge (research_only · grants/contracts HOLD)."
}
if ($GitHubRepo -notmatch "github\.com[:/]") {
    throw "GitHubRepo must be a github.com SSH/HTTPS URL."
}

$abs = Join-Path $root $ExportDir
if (-not (Test-Path $abs)) { throw "export dir missing: $abs" }

if ($RefreshMaterialize) {
    & py scripts/build_logos_oss_public_export_bundle_v1.py --materialize --out-dir $ExportDir
    if ($LASTEXITCODE -ne 0) { throw "materialize failed (exit $LASTEXITCODE)" }
}

if ($VerifyChain) {
    & py scripts/check_mkm_secret_patterns_v1.py
    if ($LASTEXITCODE -ne 0) { throw "secret pattern check failed (exit $LASTEXITCODE)" }
    & py scripts/build_logos_oss_public_export_bundle_v1.py --verify-only
    if ($LASTEXITCODE -ne 0) { throw "export manifest verify failed (exit $LASTEXITCODE)" }
    & py scripts/run_logos_oss_premarket_smoke_v1.py --skip-secret-check
    if ($LASTEXITCODE -ne 0) { throw "premarket smoke failed (exit $LASTEXITCODE)" }
}

Push-Location $abs
try {
    $exportGit = Join-Path (Get-Location).Path ".git"
    if (-not (Test-Path $exportGit)) {
        Write-Host "[INFO] initializing isolated git repo in export dir" -ForegroundColor Cyan
        git init -b main
        git add -A
        git commit -m "feat(logos): open-core conflict/synthesis harness (OPEN_SOURCE_PREP)"
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
                --description "Logos Research open-core: conflict retrieval + synthesis harness (research_only · SEND_GATE HOLD)" `
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
        git commit -m "chore(logos-oss): export refresh $stamp (OPEN_SOURCE_PREP)"
        if ($LASTEXITCODE -ne 0) { throw "export commit failed (exit $LASTEXITCODE)" }
        Write-Host "[INFO] committed export changes before push" -ForegroundColor Cyan
    } else {
        Write-Host "[INFO] export tree clean — nothing to commit" -ForegroundColor DarkGray
    }

    git push -u github main
    if ($LASTEXITCODE -ne 0) { throw "git push github main failed (exit $LASTEXITCODE)" }

    Write-Host "[DONE] GitHub push OK: $GitHubRepo (branch main)" -ForegroundColor Green
    Write-Host "[NOTE] research_only · grants/contracts HOLD · not full Scriptorium/KRV/Track A." -ForegroundColor Yellow
}
finally {
    Pop-Location
}
