#Requires -Version 5.1
# VPS: sync robots.txt + apply nginx :80 origin probe fix for CF managed prepend.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipSync
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$rehearsal = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $rehearsal "sync_required_env_to_user.ps1") | Out-Null

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

$originLocal = Join-Path $rehearsal "jemaai-cloud-mvp\nginx_snippets\jemaai_robots_txt_origin_v1.conf"
$applyLocal = Join-Path $WorkspaceRoot "scripts\deploy\linux\apply_jemaai_robots_txt_origin_v1.sh"
foreach ($p in @($originLocal, $applyLocal)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "missing: $p" }
}

if (-not $SkipSync) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $rehearsal "sync_showroom_to_vps.ps1") -SkipDotenvUserSync
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$remoteOrigin = "/tmp/jemaai_robots_txt_origin_v1.conf"
$remoteApply = "/tmp/apply_jemaai_robots_txt_origin_v1.sh"

& scp @($extraArgs + @($originLocal, "${sshTarget}:${remoteOrigin}"))
if ($LASTEXITCODE -ne 0) { throw "scp origin snippet failed" }
& scp @($extraArgs + @($applyLocal, "${sshTarget}:${remoteApply}"))
if ($LASTEXITCODE -ne 0) { throw "scp apply script failed" }

$remoteCmd = "sed -i 's/\r$//' $remoteApply && chmod +x $remoteApply && JEMAAI_WEB_ROOT=$remoteRoot sudo -E bash $remoteApply $remoteOrigin"
& ssh @($extraArgs + @($sshTarget, $remoteCmd))
if ($LASTEXITCODE -ne 0) { throw "ssh apply robots origin failed: $LASTEXITCODE" }

Write-Host "[robots-origin] VPS nginx :80 robots.txt HTTP 200 OK" -ForegroundColor Green
exit 0
