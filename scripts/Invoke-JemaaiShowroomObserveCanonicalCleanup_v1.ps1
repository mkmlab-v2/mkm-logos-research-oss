# VPS: root legacy HTML cleanup + nginx observe canonical (jemaai.cloud).
# Usage: powershell -File scripts\Invoke-JemaaiShowroomObserveCanonicalCleanup_v1.ps1

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$rehearsal = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal"
$syncDotenv = Join-Path $rehearsal "sync_required_env_to_user.ps1"
$dotenvPath = Join-Path $WorkspaceRoot ".env"
if ((Test-Path $syncDotenv) -and (Test-Path $dotenvPath)) {
    powershell -NoProfile -ExecutionPolicy Bypass -File $syncDotenv | Out-Null
}

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    return ""
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
$user = Get-EnvAny "MKM_VPS_USER"
if ([string]::IsNullOrWhiteSpace($hostName) -or [string]::IsNullOrWhiteSpace($user)) {
    throw "Set MKM_VPS_HOST and MKM_VPS_USER"
}

$extraRaw = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$extraArgs = @()
if (-not [string]::IsNullOrWhiteSpace($extraRaw)) {
    $extraArgs = $extraRaw -split "\s+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
}

$sshTarget = "${user}@${hostName}"
$remoteRoot = Get-EnvAny "JEMAAI_VPS_SHOWROOM_ROOT"
if ([string]::IsNullOrWhiteSpace($remoteRoot)) { $remoteRoot = "/var/www/jemaai" }

$cleanupLocal = Join-Path $WorkspaceRoot "scripts\deploy\linux\cleanup_jemaai_showroom_root_legacy_v1.sh"
$applyLocal = Join-Path $WorkspaceRoot "scripts\deploy\linux\apply_jemaai_observe_canonical_nginx_v1.sh"
$redirectLocal = Join-Path $rehearsal "jemaai-cloud-mvp\nginx_snippets\jemaai_showroom_legacy_redirect_v1.conf"
$noindexLocal = Join-Path $rehearsal "jemaai-cloud-mvp\nginx_snippets\jemaai_showroom_legacy_noindex_v1.conf"
$uiLocal = Join-Path $rehearsal "jemaai-cloud-mvp\nginx_snippets\jemaai_showroom_ui.conf"
$apiApplyLocal = Join-Path $WorkspaceRoot "scripts\deploy\linux\apply_jemaai_api_showroom_ui_legacy_v1.sh"
foreach ($p in @($cleanupLocal, $applyLocal, $redirectLocal, $noindexLocal, $uiLocal, $apiApplyLocal)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "missing: $p" }
}

$remoteCleanup = "/tmp/cleanup_jemaai_showroom_root_legacy_v1.sh"
$remoteApply = "/tmp/apply_jemaai_observe_canonical_nginx_v1.sh"
$remoteRedirect = "/tmp/observe_legacy_redirect_v1.conf"
$remoteNoindex = "/tmp/observe_legacy_noindex_v1.conf"
$remoteUi = "/tmp/jemaai_showroom_ui.conf"
$remoteApiApply = "/tmp/apply_jemaai_api_showroom_ui_legacy_v1.sh"

if ($DryRun) {
    Write-Host "[observe-canonical] DRYRUN would scp+ssh cleanup+nginx to $sshTarget"
    exit 0
}

Write-Host "[observe-canonical] uploading scripts..." -ForegroundColor Cyan
foreach ($pair in @(
        @{ Local = $cleanupLocal; Remote = $remoteCleanup },
        @{ Local = $applyLocal; Remote = $remoteApply },
        @{ Local = $redirectLocal; Remote = $remoteRedirect },
        @{ Local = $noindexLocal; Remote = $remoteNoindex },
        @{ Local = $uiLocal; Remote = $remoteUi },
        @{ Local = $apiApplyLocal; Remote = $remoteApiApply }
    )) {
    $argv = @($extraArgs) + @($pair.Local, "${sshTarget}:$($pair.Remote)")
    & scp @argv
    if ($LASTEXITCODE -ne 0) { throw "scp failed ($($pair.Remote)): $LASTEXITCODE" }
}

$remoteCmd = @(
    "sed -i 's/\r$//' $remoteCleanup $remoteApply $remoteApiApply",
    "chmod +x $remoteCleanup $remoteApply $remoteApiApply",
    "JEMAAI_WEB_ROOT=$remoteRoot sudo -E bash $remoteCleanup",
    "sudo bash $remoteApply $remoteRedirect $remoteNoindex",
    "sudo bash $remoteApiApply $remoteUi"
) -join " && "

Write-Host "[observe-canonical] running cleanup + nginx on $sshTarget" -ForegroundColor Cyan
& ssh @($extraArgs + @($sshTarget, $remoteCmd))
if ($LASTEXITCODE -ne 0) { throw "remote cleanup/nginx failed: $LASTEXITCODE" }

Write-Host "[observe-canonical] OK" -ForegroundColor Green
