<#
.SYNOPSIS
  Local one-command ship to VPS with Git sync guardrails.

.DESCRIPTION
  1) Validate local repo status
  2) Push local HEAD to origin/main (optional skip)
  3) SSH into VPS and run deploy verifier script

.PARAMETER LocalRepoPath
  Local repository root path.

.PARAMETER VpsHost
  SSH host alias or IP for VPS.

.PARAMETER VpsRepoPath
  Canonical repository path on VPS.

.PARAMETER Branch
  Target branch to deploy. Default: main

.PARAMETER VpsUser
  Optional SSH user. If empty, SSH config/default user is used.

.PARAMETER IdentityFile
  Optional SSH key path.

.PARAMETER AllowDirty
  Allow local dirty working tree for emergency deploy.

.PARAMETER SkipPush
  Skip git push step.

.PARAMETER DryRun
  Print commands without executing remote deploy script.

.PARAMETER ReloadCmd
  Optional command executed on VPS after successful fast-forward pull.
#>
param(
    [string]$LocalRepoPath = "C:\workspace",
    [string]$VpsHost = "vps-mkmlife",
    [string]$VpsRepoPath = "/opt/mkm-lab-workspace-v2",
    [string]$Branch = "main",
    [string]$VpsUser = "",
    [string]$IdentityFile = "",
    [switch]$AllowDirty,
    [switch]$SkipPush,
    [switch]$DryRun,
    [string]$ReloadCmd = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $LocalRepoPath)) {
    throw "LocalRepoPath not found: $LocalRepoPath"
}

Push-Location $LocalRepoPath
try {
    git rev-parse --git-dir | Out-Null

    $dirty = git status --porcelain
    if ($dirty -and -not $AllowDirty) {
        throw "Local working tree is dirty. Commit/stash first or pass -AllowDirty."
    }

    git fetch origin --prune | Out-Null
    $localHead = (git rev-parse HEAD).Trim()

    if (-not $SkipPush) {
        Write-Host "[SHIP] Pushing local HEAD to origin/$Branch..." -ForegroundColor Cyan
        git push origin "HEAD:$Branch"
    } else {
        Write-Host "[SHIP] SkipPush enabled. Push step skipped." -ForegroundColor Yellow
    }

    git fetch origin --prune | Out-Null
    $originHead = (git rev-parse "refs/remotes/origin/$Branch").Trim()
    if ($localHead -ne $originHead -and -not $SkipPush) {
        throw "Post-push verification failed: local HEAD != origin/$Branch"
    }

    $target = if ($VpsUser) { "$VpsUser@$VpsHost" } else { $VpsHost }
    $sshArgs = @()
    if ($IdentityFile) {
        if (-not (Test-Path -LiteralPath $IdentityFile)) {
            throw "Identity file not found: $IdentityFile"
        }
        $sshArgs += @("-i", $IdentityFile)
    }
    $sshArgs += @("-o", "StrictHostKeyChecking=accept-new")
    $sshArgs += $target

    $remoteScript = "$VpsRepoPath/scripts/deploy/linux/verify_and_reload.sh"
    $escapedReload = $ReloadCmd.Replace("'", "'\''")
    $reloadArg = if ($ReloadCmd) { " --reload-cmd '$escapedReload'" } else { "" }
    $remoteCmd = "set -e; if [ ! -f '$remoteScript' ]; then echo 'missing script: $remoteScript' >&2; exit 2; fi; bash '$remoteScript' --repo-path '$VpsRepoPath' --branch '$Branch'$reloadArg"

    Write-Host "[SHIP] Remote target: $target" -ForegroundColor Cyan
    Write-Host "[SHIP] Remote command: $remoteCmd" -ForegroundColor DarkGray

    if ($DryRun) {
        Write-Host "[SHIP] DryRun enabled. Remote deploy script not executed." -ForegroundColor Yellow
        exit 0
    }

    & ssh @sshArgs $remoteCmd
    if ($LASTEXITCODE -ne 0) {
        throw "Remote deploy script failed (ssh exit code: $LASTEXITCODE)"
    }

    Write-Host "[SHIP] SUCCESS: local->origin->vps deploy completed." -ForegroundColor Green
}
finally {
    Pop-Location
}
