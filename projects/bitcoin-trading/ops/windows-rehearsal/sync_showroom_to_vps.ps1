# Push local showroom static assets (poll + minimal board + bundle JSON) to VPS web root via scp (OpenSSH).
#
# Prereq: Windows OpenSSH Client (scp/ssh on PATH).
#
# By default, runs sync_required_env_to_user.ps1 first so MKM_VPS_* from C:\workspace\.env
# are written to Windows User scope (same hub as OPS bootstrap). Use -SkipDotenvUserSync to disable.
#
# Required env (Process or User):
#   MKM_VPS_HOST, MKM_VPS_USER
# Optional env:
#   JEMAAI_VPS_SHOWROOM_ROOT — remote directory (default /var/www/jemaai)
#   MKM_VPS_SCP_EXTRA_ARGS   — extra scp args, e.g. -i C:\Users\me\.ssh\id_ed25519
#   JEMAAI_VPS_RELOAD_NGINX  — set to 1 to run "sudo nginx -t && sudo systemctl reload nginx" after scp
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File sync_showroom_to_vps.ps1
#   powershell ... -RefreshStaging   # chain (freshness -> build -> validate) -> deploy_showroom_static -> scp
#   powershell ... -DryRun
#   powershell ... -SkipDotenvUserSync

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$RefreshStaging,
    [switch]$DryRun,
    [switch]$SkipDotenvUserSync,
    [switch]$AllowPasswordPrompt
)

$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$syncDotenv = Join-Path $here "sync_required_env_to_user.ps1"
$dotenvPath = Join-Path $WorkspaceRoot ".env"
if (-not $SkipDotenvUserSync -and (Test-Path -LiteralPath $syncDotenv) -and (Test-Path -LiteralPath $dotenvPath)) {
    Write-Host "[showroom-vps-sync] Applying .env -> User env (sync_required_env_to_user.ps1)..." -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File $syncDotenv
    if ($LASTEXITCODE -ne 0) {
        throw "[showroom-vps-sync] sync_required_env_to_user.ps1 failed: $LASTEXITCODE"
    }
}

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    return ""
}

function Assert-Command([string]$name) {
    $cmd = Get-Command -Name $name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "[showroom-vps-sync] missing '$name' on PATH (install OpenSSH Client)."
    }
}

Assert-Command -name "scp"
Assert-Command -name "ssh"

$staging = Join-Path $here ".showroom_staging"
$html = Join-Path $staging "public_showroom_poll.html"
$htmlMinimal = Join-Path $staging "public_showroom_board_minimal.html"
$json = Join-Path $staging "showroom_public_bundle_v1.json"
$jsonTopology = Join-Path $staging "showroom_topology_radar_snapshot_v1_latest.json"

if ($RefreshStaging) {
    Write-Host "[showroom-vps-sync] RefreshStaging: track_c chain -> deploy_showroom_static" -ForegroundColor Cyan
    $chain = Join-Path $WorkspaceRoot "scripts\build_showroom_track_c_bundle_chain_v1.ps1"
    $deploy = Join-Path $here "deploy_showroom_static.ps1"
    $bundleOut = Join-Path $WorkspaceRoot "docs\final\artifacts\showroom_public_bundle_v1.json"

    if ($DryRun) {
        Write-Host "[showroom-vps-sync] DRYRUN would run: $chain -WorkspaceRoot $WorkspaceRoot ; $deploy"
    } else {
        if (-not (Test-Path -LiteralPath $chain)) {
            throw "Missing chain script: $chain"
        }
        $psExe = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell.exe" }
        & $psExe -NoProfile -ExecutionPolicy Bypass -File $chain -WorkspaceRoot $WorkspaceRoot
        if ($LASTEXITCODE -ne 0) { throw "build_showroom_track_c_bundle_chain_v1.ps1 failed: $LASTEXITCODE" }
        powershell -NoProfile -ExecutionPolicy Bypass -File $deploy -WorkspaceRoot $WorkspaceRoot
        if ($LASTEXITCODE -ne 0) { throw "deploy_showroom_static.ps1 failed: $LASTEXITCODE" }
    }
}

if (-not (Test-Path -LiteralPath $html) -or -not (Test-Path -LiteralPath $htmlMinimal) -or -not (Test-Path -LiteralPath $json)) {
    throw "[showroom-vps-sync] staging files missing under $staging — run deploy_showroom_static.ps1 or use -RefreshStaging."
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
$user = Get-EnvAny "MKM_VPS_USER"
if ([string]::IsNullOrWhiteSpace($hostName) -or [string]::IsNullOrWhiteSpace($user)) {
    throw "[showroom-vps-sync] set MKM_VPS_HOST and MKM_VPS_USER (Process or User env)."
}

$remoteRoot = Get-EnvAny "JEMAAI_VPS_SHOWROOM_ROOT"
if ([string]::IsNullOrWhiteSpace($remoteRoot)) {
    $remoteRoot = "/var/www/jemaai"
}
$remoteRoot = $remoteRoot.TrimEnd("/")

$extraRaw = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$extraArgs = @()
if (-not [string]::IsNullOrWhiteSpace($extraRaw)) {
    $extraArgs = $extraRaw -split "\s+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
}

function Test-HasIdentityArgs([string[]]$args) {
    for ($i = 0; $i -lt $args.Count; $i++) {
        $arg = $args[$i]
        if ($arg -eq "-i") { return $true }
        if ($arg -like "-i*") { return $true }
        if ($arg -eq "-o" -and ($i + 1) -lt $args.Count) {
            $next = $args[$i + 1]
            if ($next -like "IdentityFile=*") { return $true }
        }
        if ($arg -like "IdentityFile=*") { return $true }
    }
    return $false
}

Write-Host "[showroom-vps-sync] remote_root=$remoteRoot host=$hostName user=$user" -ForegroundColor Cyan

# Single scp session (one password prompt when using password auth; static files -> same remote dir).
function Invoke-ScpShowroomPair {
    $remoteDir = "${user}@${hostName}:${remoteRoot}/"
    $argv = @()
    foreach ($a in $extraArgs) { $argv += $a }
    $argv += $html
    $argv += $htmlMinimal
    $argv += $json
    if (Test-Path -LiteralPath $jsonTopology) {
        $argv += $jsonTopology
    } else {
        Write-Host "[showroom-vps-sync] topology snapshot not in staging (optional): $jsonTopology" -ForegroundColor DarkGray
    }
    $argv += $remoteDir
    if ($DryRun) {
        Write-Host "[showroom-vps-sync] DRYRUN scp $($argv -join ' ')"
        return
    }
    $hasIdentity = Test-HasIdentityArgs -args $extraArgs
    if (-not $AllowPasswordPrompt -and -not $hasIdentity) {
        throw "[showroom-vps-sync] blocked: non-interactive mode requires key auth. Set MKM_VPS_SCP_EXTRA_ARGS (e.g. '-i C:\Users\<user>\.ssh\id_ed25519') or re-run with -AllowPasswordPrompt."
    }
    & scp @argv
    if ($LASTEXITCODE -ne 0) {
        throw "[showroom-vps-sync] scp failed ($LASTEXITCODE)"
    }
}

Invoke-ScpShowroomPair

$reload = Get-EnvAny "JEMAAI_VPS_RELOAD_NGINX"
if ($reload -eq "1") {
    $sshTarget = "${user}@${hostName}"
    $remoteCmd = "sudo nginx -t && sudo systemctl reload nginx"
    if ($DryRun) {
        Write-Host "[showroom-vps-sync] DRYRUN ssh ... $sshTarget $remoteCmd"
    } else {
        Write-Host "[showroom-vps-sync] reloading nginx on host..." -ForegroundColor Cyan
        & ssh @($extraArgs + @($sshTarget, $remoteCmd))
        if ($LASTEXITCODE -ne 0) {
            throw "[showroom-vps-sync] ssh nginx reload failed: $LASTEXITCODE"
        }
    }
} else {
    Write-Host "[showroom-vps-sync] nginx reload skipped (set JEMAAI_VPS_RELOAD_NGINX=1 to enable)." -ForegroundColor DarkGray
}

if ($DryRun) {
    Write-Host "[showroom-vps-sync] DRYRUN complete (no files transferred)." -ForegroundColor Green
} else {
    Write-Host "[showroom-vps-sync] OK: pushed static showroom files to ${user}@${hostName}:${remoteRoot}/" -ForegroundColor Green
}
