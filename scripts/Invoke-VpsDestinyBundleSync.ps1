#Requires -Version 5.1
<#
.SYNOPSIS
  GitHub-minimal sync: ship local commits to VPS destiny repo via git bundle.

.DESCRIPTION
  Use when VPS cannot directly reach local bare/internal remote. This keeps GitHub push optional:
  1) Build bundle from local source ref (incremental against BaseRef when possible)
  2) scp bundle to VPS
  3) fetch+merge into VPS destiny checkout

  Default target:
    root@srv1101456.hstgr.cloud:/opt/mkm-destiny-ai-41e38ec6

.PARAMETER SourceRef
  Local ref to sync (default: HEAD).

.PARAMETER BaseRef
  Preferred prerequisite/base ref for incremental bundle (default: origin/main).
  If BaseRef is not an ancestor of SourceRef, script falls back to full bundle.

.PARAMETER VpsHost
  VPS hostname.

.PARAMETER VpsUser
  VPS SSH user.

.PARAMETER SshKeyPath
  SSH private key path.

.PARAMETER VpsRepoPath
  Destiny repository path on VPS.

.PARAMETER KeepBundle
  Keep local bundle file in reports/ after sync.

.PARAMETER DryRun
  Print commands without executing remote changes.
#>
param(
    [string]$SourceRef = "HEAD",
    [string]$BaseRef = "origin/main",
    [string]$VpsHost = "srv1101456.hstgr.cloud",
    [string]$VpsUser = "root",
    [string]$SshKeyPath = "$env:USERPROFILE\.ssh\hostinger_mkmlife",
    [string]$VpsRepoPath = "/opt/mkm-destiny-ai-41e38ec6",
    [switch]$KeepBundle,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repoRoot = "C:\workspace"
Set-Location $repoRoot

if (-not (Test-Path -LiteralPath (Join-Path $repoRoot ".git"))) {
    throw "Expected git repo at $repoRoot"
}
if (-not (Test-Path -LiteralPath $SshKeyPath)) {
    throw "SSH key not found: $SshKeyPath"
}

$bundleDir = Join-Path $repoRoot "reports"
New-Item -ItemType Directory -Path $bundleDir -Force | Out-Null
$bundlePath = Join-Path $bundleDir "destiny_sync_latest.bundle"

$sourceSha = (git rev-parse $SourceRef).Trim()
if (-not $sourceSha) { throw "Could not resolve SourceRef: $SourceRef" }

$baseResolved = $null
$incremental = $false
try {
    $baseResolved = (git rev-parse $BaseRef).Trim()
    & git merge-base --is-ancestor $baseResolved $sourceSha | Out-Null
    if ($LASTEXITCODE -eq 0) { $incremental = $true }
}
catch {
    $incremental = $false
}

$tipTag = "_vpssync_tip"
$baseTag = "_vpssync_base"

Write-Host "[INFO] SourceRef: $SourceRef ($sourceSha)" -ForegroundColor Cyan
if ($incremental) {
    Write-Host "[INFO] BaseRef:   $BaseRef ($baseResolved) [incremental]" -ForegroundColor Cyan
} else {
    Write-Host "[INFO] BaseRef:   $BaseRef (not usable; full bundle fallback)" -ForegroundColor Yellow
}

if ($DryRun) {
    Write-Host "[DRY] git tag -f $tipTag $sourceSha"
    if ($incremental) { Write-Host "[DRY] git tag -f $baseTag $baseResolved" }
    if ($incremental) {
        Write-Host "[DRY] git bundle create $bundlePath $baseTag..$tipTag"
    } else {
        Write-Host "[DRY] git bundle create $bundlePath $tipTag"
    }
    Write-Host "[DRY] scp -i `"$SshKeyPath`" $bundlePath ${VpsUser}@${VpsHost}:/root/destiny_sync_latest.bundle"
    Write-Host "[DRY] ssh -i `"$SshKeyPath`" $VpsUser@$VpsHost <fetch+merge commands>"
    exit 0
}

try {
    & git tag -f $tipTag $sourceSha | Out-Null
    if ($incremental) { & git tag -f $baseTag $baseResolved | Out-Null }

    if ($incremental) {
        & git bundle create $bundlePath "$baseTag..$tipTag"
    } else {
        & git bundle create $bundlePath $tipTag
    }
    if ($LASTEXITCODE -ne 0) { throw "git bundle create failed (exit $LASTEXITCODE)" }
}
finally {
    $tipExists = & git rev-parse -q --verify "refs/tags/$tipTag" 2>$null
    if ($LASTEXITCODE -eq 0 -and $tipExists) {
        & git tag -d $tipTag | Out-Null
    }
    $baseExists = & git rev-parse -q --verify "refs/tags/$baseTag" 2>$null
    if ($LASTEXITCODE -eq 0 -and $baseExists) {
        & git tag -d $baseTag | Out-Null
    }
}

if (-not (Test-Path -LiteralPath $bundlePath)) {
    throw "Bundle not created: $bundlePath"
}

$sshTarget = "$VpsUser@$VpsHost"
$remoteBundle = "/root/destiny_sync_latest.bundle"

Write-Host "[STEP] Upload bundle -> ${sshTarget}:${remoteBundle}" -ForegroundColor Yellow
& scp -i $SshKeyPath -o ConnectTimeout=30 $bundlePath "${sshTarget}:${remoteBundle}"
if ($LASTEXITCODE -ne 0) { throw "scp failed (exit $LASTEXITCODE)" }

$localRemoteScript = Join-Path $env:TEMP "run_destiny_bundle_sync.sh"
$remoteRemoteScript = "/root/run_destiny_bundle_sync.sh"
$remoteScriptBody = @"
#!/usr/bin/env bash
set -euo pipefail
cd "$VpsRepoPath"
git bundle verify "$remoteBundle" >/dev/null
git fetch "$remoteBundle" "refs/tags/${tipTag}:refs/remotes/bundle/vpssync-tip"
git merge refs/remotes/bundle/vpssync-tip -m "sync: bundle from local workstation (github-minimal)" --no-edit
git rev-parse --short HEAD
python3 - <<'PY'
from pathlib import Path
p = Path("projects/bitcoin-trading/src/futures_engine")
print("futures_engine_py_count", len(list(p.rglob("*.py"))))
PY
"@
[System.IO.File]::WriteAllText(
    $localRemoteScript,
    ($remoteScriptBody -replace "`r`n", "`n"),
    (New-Object System.Text.UTF8Encoding($false))
)

Write-Host "[STEP] Upload remote merge script" -ForegroundColor Yellow
& scp -i $SshKeyPath -o ConnectTimeout=30 $localRemoteScript "${sshTarget}:${remoteRemoteScript}"
if ($LASTEXITCODE -ne 0) { throw "scp remote script failed (exit $LASTEXITCODE)" }

Write-Host "[STEP] Fetch+merge on VPS destiny repo" -ForegroundColor Yellow
& ssh -i $SshKeyPath -o ConnectTimeout=15 -o BatchMode=yes $sshTarget "bash $remoteRemoteScript"
if ($LASTEXITCODE -ne 0) { throw "VPS merge step failed (exit $LASTEXITCODE)" }

Remove-Item -LiteralPath $localRemoteScript -Force -ErrorAction SilentlyContinue

if (-not $KeepBundle) {
    Remove-Item -LiteralPath $bundlePath -Force -ErrorAction SilentlyContinue
}

Write-Host "[DONE] VPS destiny bundle sync completed." -ForegroundColor Green
