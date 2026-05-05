<#
.SYNOPSIS
  One-command deploy for bitcoin-trading runtime on VPS.

.DESCRIPTION
  Wraps scripts/deploy/ship_to_vps.ps1 with bitcoin-trading friendly defaults:
  - local repo: C:\workspace
  - vps repo: /opt/mkm-destiny-ai-41e38ec6 (with auto-detect fallback)
  - branch: main
  - push remote: hq
  - PM2 app restart: bitcoin-live-small-24h

  Typical usage:
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy/ship_bitcoin_trading_vps.ps1
#>
param(
    [string]$VpsHost = "vps-mkmlife",
    [string]$VpsUser = "",
    [string]$IdentityFile = "",
    [string]$LocalRepoPath = "C:\workspace",
    [string]$VpsRepoPath = "/opt/mkm-destiny-ai-41e38ec6",
    [switch]$AutoDetectVpsRepoPath = $true,
    [string]$Branch = "main",
    [string]$PushRemote = "hq",
    [string]$Pm2AppName = "bitcoin-live-small-24h",
    [switch]$RunLocalPostCheck,
    [switch]$AllowStaleWindowWarning,
    [switch]$SkipPush,
    [switch]$AllowDirty,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$shipScript = Join-Path $PSScriptRoot "ship_to_vps.ps1"
if (-not (Test-Path -LiteralPath $shipScript)) {
    throw "Missing required script: $shipScript"
}

$reloadCmd = ""
if ($Pm2AppName) {
    # Explicit app-only restart; never restart all.
    $reloadCmd = "pm2 restart $Pm2AppName"
}

function Resolve-VpsTarget {
    param(
        [string]$HostName,
        [string]$UserName
    )
    if ($UserName) { return "$UserName@$HostName" }
    return $HostName
}

function Resolve-VpsRepoPath {
    param(
        [string]$Target,
        [string]$PreferredPath
    )
    $candidates = @(
        $PreferredPath,
        "/opt/mkm-destiny-ai-41e38ec6",
        "/opt/mkm-lab-workspace-v2",
        "/opt/bitcoin-trading"
    ) | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique

    foreach ($p in $candidates) {
        $cmd = "test -f '$p/scripts/deploy/linux/verify_and_reload.sh' && echo OK:$p"
        $prevNative = $PSNativeCommandUseErrorActionPreference
        $PSNativeCommandUseErrorActionPreference = $false
        try {
            $out = & ssh -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR $Target $cmd 2>$null
        }
        finally {
            $PSNativeCommandUseErrorActionPreference = $prevNative
        }
        if ($LASTEXITCODE -eq 0 -and "$out" -match "^OK:") {
            return $p
        }
    }
    return ""
}

$target = Resolve-VpsTarget -HostName $VpsHost -UserName $VpsUser
if ($AutoDetectVpsRepoPath) {
    $resolvedPath = Resolve-VpsRepoPath -Target $target -PreferredPath $VpsRepoPath
    if (-not $resolvedPath) {
        throw "Could not auto-detect VPS repo path containing scripts/deploy/linux/verify_and_reload.sh"
    }
    Write-Host "[BT-SHIP] auto-detected VpsRepoPath: $resolvedPath" -ForegroundColor Cyan
    $VpsRepoPath = $resolvedPath
}

$argsList = @(
    "-LocalRepoPath", $LocalRepoPath,
    "-VpsHost", $VpsHost,
    "-VpsRepoPath", $VpsRepoPath,
    "-Branch", $Branch,
    "-PushRemote", $PushRemote
)
if ($VpsUser) { $argsList += @("-VpsUser", $VpsUser) }
if ($IdentityFile) { $argsList += @("-IdentityFile", $IdentityFile) }
if ($reloadCmd) { $argsList += @("-ReloadCmd", $reloadCmd) }
if ($SkipPush) { $argsList += "-SkipPush" }
if ($AllowDirty) { $argsList += "-AllowDirty" }
if ($DryRun) { $argsList += "-DryRun" }

Write-Host "[BT-SHIP] invoking ship_to_vps with bitcoin-trading defaults..." -ForegroundColor Cyan
if ($reloadCmd) {
    Write-Host "[BT-SHIP] reload command: $reloadCmd" -ForegroundColor DarkGray
} else {
    Write-Host "[BT-SHIP] reload command not set. Use -Pm2AppName <name> to restart only target app." -ForegroundColor Yellow
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $shipScript @argsList
$shipExit = $LASTEXITCODE
if ($shipExit -ne 0) {
    Write-Host "[BT-SHIP] ship_to_vps failed." -ForegroundColor Red
    Write-Host "[BT-SHIP] common fixes:" -ForegroundColor Yellow
    Write-Host "  1) push remote mismatch -> set -PushRemote hq (or correct remote)" -ForegroundColor Yellow
    Write-Host "  2) dirty tree block -> add -AllowDirty or clean local changes" -ForegroundColor Yellow
    Write-Host "  3) wrong VPS repo path -> add -AutoDetectVpsRepoPath" -ForegroundColor Yellow
    Write-Host "  4) VPS main diverged -> align server repo before deploy" -ForegroundColor Yellow
    throw "ship_to_vps failed with exit code $shipExit"
}

if ($RunLocalPostCheck) {
    $opsScript = Join-Path $LocalRepoPath "projects\bitcoin-trading\ops\windows-rehearsal\run_live_ops_health_orchestrator.py"
    if (-not (Test-Path -LiteralPath $opsScript)) {
        throw "Post-check script not found: $opsScript"
    }

    $postArgs = @(
        $opsScript,
        "--out",
        "projects\bitcoin-trading\memory\v2\ops\live_ops_health_orchestrator_latest.json"
    )
    if ($AllowStaleWindowWarning) {
        $postArgs += "--allow-stale-window-warning"
    }

    Write-Host "[BT-SHIP] running local post-check orchestrator..." -ForegroundColor Cyan
    Push-Location $LocalRepoPath
    try {
        & py @postArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Local post-check failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host "[BT-SHIP] SUCCESS" -ForegroundColor Green

