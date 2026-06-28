#Requires -Version 5.1
<#
.SYNOPSIS
  Push curated Logos Research OSS export to GitHub (explicit gate only).

.EXAMPLE
  pwsh -NoProfile -File scripts/Push-LogosOssPublicToGitHub_v1.ps1 `
    -RefreshMaterialize -VerifyChain -CreateRepoIfMissing -Acknowledge

.NOTES
  Uses isolated push dir exports/_push-mkm-logos-research-oss (not monorepo git).
  Export SSOT: docs/final/artifacts/logos_oss_public_export_manifest_v1.json
#>
param(
    [string]$ExportDir = "exports/_push-mkm-logos-research-oss",
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

if ($RefreshMaterialize) {
    if (Test-Path $abs) {
        Remove-Item -Recurse -Force $abs
    }
    & py scripts/build_logos_oss_public_export_bundle_v1.py --materialize --out-dir $ExportDir
    if ($LASTEXITCODE -ne 0) { throw "materialize failed (exit $LASTEXITCODE)" }
}

if (-not (Test-Path $abs)) { throw "export dir missing: $abs (run with -RefreshMaterialize)" }

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
    if (Test-Path ".git") { Remove-Item -Recurse -Force ".git" }
    git init -b main
    if ($LASTEXITCODE -ne 0) { throw "git init failed (exit $LASTEXITCODE)" }

    $topLevel = (git rev-parse --show-toplevel).Replace("\", "/")
    $cwd = (Get-Location).Path.Replace("\", "/")
    if ($topLevel -ne $cwd) {
        throw "git isolation failed: toplevel=$topLevel cwd=$cwd"
    }

    git add -A
    git commit -m "feat(logos): open-core conflict/synthesis harness (OPEN_SOURCE_PREP)"
    if ($LASTEXITCODE -ne 0) { throw "export commit failed (exit $LASTEXITCODE)" }

    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    gh repo view $GitHubOwnerRepo 1>$null 2>$null
    $repoExists = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEap

    if (-not $repoExists) {
        if (-not $CreateRepoIfMissing) {
            throw "GitHub repo missing: $GitHubOwnerRepo (use -CreateRepoIfMissing)"
        }
        Write-Host "[INFO] creating public repo $GitHubOwnerRepo" -ForegroundColor Cyan
        gh repo create $GitHubOwnerRepo --public `
            --description "Logos Research open-core: conflict retrieval + synthesis harness (research_only · SEND_GATE HOLD)" `
            --source . --remote github
        if ($LASTEXITCODE -ne 0) { throw "gh repo create failed (exit $LASTEXITCODE)" }
    } else {
        $ErrorActionPreference = "Continue"
        git remote get-url github 2>$null | Out-Null
        $hasRemote = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = $prevEap
        if (-not $hasRemote) {
            git remote add github $GitHubRepo
        }
        git push -u github main --force
        if ($LASTEXITCODE -ne 0) { throw "git push github main failed (exit $LASTEXITCODE)" }
    }

    Write-Host "[DONE] GitHub push OK: $GitHubRepo (branch main)" -ForegroundColor Green
    Write-Host "[NOTE] research_only · grants/contracts HOLD · not full Scriptorium/KRV/Track A." -ForegroundColor Yellow
}
finally {
    Pop-Location
}
