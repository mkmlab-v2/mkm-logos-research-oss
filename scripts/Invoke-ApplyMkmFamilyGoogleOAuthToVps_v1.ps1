<#
.SYNOPSIS
  Push MKM Family OAuth env keys from local DPAPI to VPS no1kmedi .env.local (no secret stdout).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ApplyMkmFamilyGoogleOAuthToVps_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$SshIdentityFile = "",
    [switch]$DryRun,
    [switch]$SkipPm2Restart
)

$ErrorActionPreference = "Stop"

function Get-EnvAny([string]$name) {
    foreach ($scope in @("Process", "User", "Machine")) {
        $v = [Environment]::GetEnvironmentVariable($name, $scope)
        if ($v) { return $v.Trim() }
    }
    return ""
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
if (-not $hostName) { $hostName = "vps-mkmlife" }
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$remote = "${user}@${hostName}"
$vpsDest = "/opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi"

$applyLocal = Join-Path $WorkspaceRoot "scripts\Invoke-ApplyMkmFamilyGoogleOAuthFromDpapi_v1.ps1"
$envLocal = Join-Path $WorkspaceRoot "projects\no1kmedi\.env.local"

if (-not $DryRun) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $applyLocal -WorkspaceRoot $WorkspaceRoot -EnvLocalPath $envLocal
    if ($LASTEXITCODE -ne 0) { throw "Local DPAPI apply failed (exit $LASTEXITCODE)" }
}

if (-not (Test-Path $envLocal)) { throw "Missing $envLocal after local apply" }

$keys = @("MKM_FAMILY_AUTH_SECRET", "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET")
$lines = Get-Content -Path $envLocal -Encoding UTF8
$payload = @()
foreach ($k in $keys) {
    $match = $lines | Where-Object { $_ -match "^\s*$([regex]::Escape($k))\s*=" } | Select-Object -First 1
    if (-not $match) {
        Write-Host "[mkm-family-vps] missing $k in $envLocal — store Google OAuth keys in DPAPI first" -ForegroundColor Yellow
        exit 1
    }
    $payload += $match
}

$sshArgs = @()
if ($SshIdentityFile) { $sshArgs = @("-i", $SshIdentityFile) }
else {
    $extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
    if ($extra) { $sshArgs = $extra -split "\s+" | Where-Object { $_ } }
}

$remoteScript = @"
ENV_FILE='$vpsDest/.env.local'
touch "`$ENV_FILE"
"@
foreach ($line in $payload) {
    $name = ($line -split "=", 2)[0].Trim()
    $escaped = ($line -replace "'", "'\\''")
    $remoteScript += @"

grep -q '^${name}=' "`$ENV_FILE" && sed -i 's|^${name}=.*|${escaped}|' "`$ENV_FILE" || echo '${escaped}' >> "`$ENV_FILE"
"@
}
if (-not $SkipPm2Restart) {
    $remoteScript += @"

pm2 restart no1kmedi-com --update-env || true
pm2 save || true
"@
}

if ($DryRun) {
    Write-Host "[DRY] Would ssh $remote and update $($keys -join ', ')" -ForegroundColor Cyan
    exit 0
}

Write-Host "[mkm-family-vps] updating VPS .env.local ($($keys.Count) keys)" -ForegroundColor Cyan
& ssh @($sshArgs + @($remote, $remoteScript))
if ($LASTEXITCODE -ne 0) { throw "ssh failed exit $LASTEXITCODE" }
Write-Host "[mkm-family-vps] OK (secrets not printed)" -ForegroundColor Green
