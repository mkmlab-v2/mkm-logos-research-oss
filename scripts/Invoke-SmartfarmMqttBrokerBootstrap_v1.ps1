#Requires -Version 5.1
<#
.SYNOPSIS
  VPS Mosquitto install + optional PM2 MQTT subscriber bootstrap (tier_0 SSH).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-SmartfarmMqttBrokerBootstrap_v1.ps1
  powershell -File scripts\Invoke-SmartfarmMqttBrokerBootstrap_v1.ps1 -WhatIfOnly
#>
param(
    [switch]$StartSubscriber,
    [switch]$WhatIfOnly,
    [string]$RepoRoot = "/opt/mkm-destiny-ai-41e38ec6"
)

$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "C:\workspace" }
Set-Location $root

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($v) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if ($v) { return $v.Trim() }
    return ""
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
if (-not $hostName) { $hostName = "vps-mkmlife" }
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$remote = "${user}@${hostName}"
$installScript = Join-Path $root "scripts\deploy\linux\install_smartfarm_mosquitto_v1.sh"
$outJson = Join-Path $root "reports\smartfarm_mqtt_broker_bootstrap_v1_latest.json"

if (-not (Test-Path -LiteralPath $installScript)) {
    Write-Error "Missing $installScript"
}

$subFlag = if ($StartSubscriber) { "--start-subscriber" } else { "" }

if ($WhatIfOnly) {
    Write-Host "[smartfarm-mqtt] WhatIf: scp install script + sudo bash on $remote"
    exit 0
}

$extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$sshArgs = @()
if ($extra) { $sshArgs = $extra -split "\s+" | Where-Object { $_ } }

$remoteScript = "/tmp/install_smartfarm_mosquitto_v1.sh"
$lfScript = Join-Path $env:TEMP "install_smartfarm_mosquitto_v1_lf.sh"
$content = [System.IO.File]::ReadAllText($installScript) -replace "`r`n", "`n" -replace "`r", "`n"
[System.IO.File]::WriteAllText($lfScript, $content, (New-Object System.Text.UTF8Encoding $false))
& scp @($sshArgs + @($lfScript, "${remote}:${remoteScript}"))

$spineFiles = @(
    "scripts\deploy\linux\pm2_smartfarm_mqtt_subscriber.config.cjs",
    "scripts\smartfarm_qubics_mqtt_subscriber_v1.py",
    "scripts\smartfarm_qubics_mqtt_uplink_v1.py",
    "scripts\smartfarm_qubics_mqtt_control_v1.py",
    "scripts\smartfarm_qubics_device_resolver_v1.py",
    "docs\final\artifacts\smartfarm_qubics_device_manifest_v1.json",
    "docs\final\artifacts\smartfarm_qubics_mqtt_control_spec_v1.example.json"
)
foreach ($rel in $spineFiles) {
    $local = Join-Path $root $rel
    if (-not (Test-Path -LiteralPath $local)) {
        Write-Warning "[smartfarm-mqtt] skip missing $rel"
        continue
    }
    $remotePath = "$RepoRoot/" + ($rel -replace '\\', '/')
    $remoteDir = ($remotePath -replace '/[^/]+$', '')
    & ssh @($sshArgs + @($remote, "mkdir -p '$remoteDir'"))
    & scp @($sshArgs + @($local, "${remote}:${remotePath}"))
    if ($LASTEXITCODE -ne 0) { throw "scp failed for $rel exit $LASTEXITCODE" }
}
Write-Host "[smartfarm-mqtt] spine files synced" -ForegroundColor Cyan
if ($LASTEXITCODE -ne 0) { throw "scp install script failed exit $LASTEXITCODE" }

$remoteCmd = "chmod +x $remoteScript && REPO_ROOT='$RepoRoot' bash $remoteScript $subFlag"
Write-Host "[smartfarm-mqtt] VPS mosquitto install" -ForegroundColor Cyan
& ssh @($sshArgs + @($remote, $remoteCmd))
$sshCode = if ($null -eq $LASTEXITCODE) { 1 } else { $LASTEXITCODE }

$doc = [ordered]@{
    schema           = "smartfarm_mqtt_broker_bootstrap_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    host             = $hostName
    repo_root        = $RepoRoot
    start_subscriber = [bool]$StartSubscriber
    ok               = ($sshCode -eq 0)
    reproduce        = "powershell -File scripts\Invoke-SmartfarmMqttBrokerBootstrap_v1.ps1"
    boundary_ack     = "Localhost broker only; G300 field cid commission still Tier3 HOLD"
}
$doc | ConvertTo-Json -Depth 5 | Set-Content -Path $outJson -Encoding UTF8

if ($sshCode -ne 0) {
    Write-Host "[smartfarm-mqtt] FAIL exit=$sshCode report=$outJson" -ForegroundColor Red
    exit $sshCode
}
Write-Host "[smartfarm-mqtt] OK report=$outJson" -ForegroundColor Green
exit 0
