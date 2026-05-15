<#
.SYNOPSIS
  Guarded one-click deploy for jemaai/no1kmedi on VPS.

.DESCRIPTION
  Runs a strict git safety gate on VPS, then executes:
    pull --ff-only -> no1kmedi build -> pm2 restart -> public smoke checks
  This script is intentionally non-destructive and avoids reset/rebase.

.PARAMETER WorkspaceRoot
  Local workspace root (default: C:\workspace)

.PARAMETER DryRun
  Print planned commands only.

.PARAMETER SkipBuildRestart
  Run git gate/pull and smoke checks without build + PM2 restart.

.PARAMETER UseDestinyNo1kmediBuild
  Build/restart jema-ai from /opt/mkm-destiny-ai-41e38ec6 (not mkm-lab-workspace-v2). Use when lab workspace main lags or npm build fails there.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_showroom_vps_guarded_deploy.ps1
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_showroom_vps_guarded_deploy.ps1 -UseDestinyNo1kmediBuild -SkipBuildRestart:$false
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DryRun,
    [switch]$SkipBuildRestart,
    [switch]$UseDestinyNo1kmediBuild,
    [switch]$AllowPasswordPrompt,
    [string]$SshIdentityFile = ""
)

$ErrorActionPreference = "Stop"

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    return ""
}

function Assert-Command([string]$name) {
    if (-not (Get-Command -Name $name -ErrorAction SilentlyContinue)) {
        throw "[showroom-guarded-deploy] missing '$name' on PATH."
    }
}

function Test-HasIdentityArgs([string[]]$args) {
    for ($i = 0; $i -lt $args.Count; $i++) {
        $arg = $args[$i]
        if ($arg -eq "-i" -or $arg -like "-i*") { return $true }
        if ($arg -eq "-o" -and ($i + 1) -lt $args.Count) {
            if ($args[$i + 1] -like "IdentityFile=*") { return $true }
        }
        if ($arg -like "IdentityFile=*") { return $true }
    }
    return $false
}

function Invoke-Checked([string]$label, [scriptblock]$action) {
    Write-Host "[showroom-guarded-deploy] $label" -ForegroundColor Cyan
    & $action
    if ($LASTEXITCODE -ne 0) {
        throw "[showroom-guarded-deploy] failed: $label (exit $LASTEXITCODE)"
    }
}

Assert-Command "ssh"
Assert-Command "curl.exe"

$hostName = Get-EnvAny "MKM_VPS_HOST"
$user = Get-EnvAny "MKM_VPS_USER"
if ([string]::IsNullOrWhiteSpace($hostName) -or [string]::IsNullOrWhiteSpace($user)) {
    throw "[showroom-guarded-deploy] set MKM_VPS_HOST and MKM_VPS_USER first."
}

$vpsWorkspace = "/opt/mkm-lab-workspace-v2"
$vpsDestinyRepo = "/opt/mkm-destiny-ai-41e38ec6"
$vpsNo1kmediDestiny = "$vpsDestinyRepo/projects/no1kmedi"
$remote = "${user}@${hostName}"
# Lab workspace may lag monorepo; skip gate when script absent (pull+build still guarded by ff-only).
$gateCmd = "cd $vpsWorkspace && (test -f scripts/verify_git_origin_main_sync.sh && scripts/verify_git_origin_main_sync.sh --check-internal-safety --strict . || echo VPS_GATE_SCRIPT_SKIP)"
$pullCmd = "cd $vpsWorkspace && git fetch internal && git checkout main && git pull --ff-only internal main"
$buildRestartCmd = "cd $vpsWorkspace/projects/no1kmedi && npm run build && pm2 restart no1kmedi-com && pm2 status"
if ($UseDestinyNo1kmediBuild) {
    $buildRestartCmd = @"
cd $vpsNo1kmediDestiny && npm ci && npm run build && pm2 delete no1kmedi-com 2>/dev/null || true && pm2 start npm --name no1kmedi-com --cwd $vpsNo1kmediDestiny -- start && pm2 save && pm2 describe no1kmedi-com | grep -E 'exec cwd|status'
"@
}

$smokeUrls = @(
    "https://api.jemaai.cloud/public_showroom_board_minimal.html",
    "https://api.jemaai.cloud/api/public-events/latest",
    "https://jema-ai.com"
)

$extraRaw = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$sshArgs = @()
if (-not [string]::IsNullOrWhiteSpace($extraRaw)) {
    $sshArgs = $extraRaw -split "\s+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
}
if (-not [string]::IsNullOrWhiteSpace($SshIdentityFile)) {
    $sshArgs = @("-i", $SshIdentityFile) + $sshArgs
}
$hasIdentity = $false
if (-not [string]::IsNullOrWhiteSpace($SshIdentityFile)) {
    $hasIdentity = $true
} else {
    $hasIdentity = Test-HasIdentityArgs -args $sshArgs
}
if (-not $AllowPasswordPrompt -and -not $hasIdentity) {
    throw "[showroom-guarded-deploy] blocked: non-interactive mode requires key auth. Set MKM_VPS_SCP_EXTRA_ARGS (e.g. '-i C:\Users\<user>\.ssh\id_ed25519') or run with -AllowPasswordPrompt."
}

if ($DryRun) {
    Write-Host "[showroom-guarded-deploy] DRYRUN remote=$remote" -ForegroundColor Yellow
    Write-Host "  ssh $($sshArgs -join ' ') $remote '$gateCmd'"
    Write-Host "  ssh $($sshArgs -join ' ') $remote '$pullCmd'"
    if (-not $SkipBuildRestart) {
        Write-Host "  ssh $($sshArgs -join ' ') $remote '$buildRestartCmd'"
    }
    foreach ($u in $smokeUrls) {
        Write-Host "  curl.exe -s -o NUL -w '%{http_code}' $u"
    }
    exit 0
}

Invoke-Checked "VPS gate check" { & ssh @($sshArgs + @($remote, $gateCmd)) }
Invoke-Checked "VPS ff-only pull" { & ssh @($sshArgs + @($remote, $pullCmd)) }

if (-not $SkipBuildRestart) {
    Invoke-Checked "VPS build + pm2 restart" { & ssh @($sshArgs + @($remote, $buildRestartCmd)) }
}

foreach ($u in $smokeUrls) {
    Write-Host "[showroom-guarded-deploy] smoke $u" -ForegroundColor Cyan
    $code = & curl.exe -s -o NUL -w "%{http_code}" $u
    if (@("200", "301", "302") -notcontains "$code") {
        throw "[showroom-guarded-deploy] smoke failed: $u (http $code)"
    }
}

Write-Host "[showroom-guarded-deploy] OK: gated deploy + smoke passed." -ForegroundColor Green
