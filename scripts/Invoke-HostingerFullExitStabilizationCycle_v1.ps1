#Requires -Version 5.1
<#
.SYNOPSIS
  Hostinger full exit — Phase 3 stabilization: HTTP/DNS probe + Cloudflare health, append JSONL log.

.DESCRIPTION
  Implements plan "병행운영 모니터링": runs scripts/run_hostinger_exit_monitor_probe.ps1 with domains from
  scripts/data/hostinger_full_exit/monitor_targets_v1.json, then Invoke-CloudflareDnsHealthCheck_v1.ps1.
  Appends one line to reports/hostinger_full_exit_stabilization_log.jsonl

.PARAMETER TargetsJson
  Path to monitor_targets_v1.json (default under repo scripts/data/hostinger_full_exit/).

.PARAMETER SkipCloudflareHealth
  Only run Hostinger exit HTTP/DNS probe.

.PARAMETER LogJsonl
  Append path (default reports/hostinger_full_exit_stabilization_log.jsonl).

.NOTES
  Does not modify DNS. Safe for scheduled runs.
#>
param(
    [string]$TargetsJson = "",
    [switch]$SkipCloudflareHealth,
    [string]$LogJsonl = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($TargetsJson)) {
    $TargetsJson = Join-Path $PSScriptRoot "data\hostinger_full_exit\monitor_targets_v1.json"
}
if ([string]::IsNullOrWhiteSpace($LogJsonl)) {
    $LogJsonl = Join-Path $root "reports\hostinger_full_exit_stabilization_log.jsonl"
}

if (-not (Test-Path -LiteralPath $TargetsJson)) { throw "Missing targets file: $TargetsJson" }
$tj = Get-Content -LiteralPath $TargetsJson -Raw -Encoding UTF8 | ConvertFrom-Json
$httpsGateDomains = @($tj.domains | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
$exclP = $tj.PSObject.Properties['https_gate_exclusions']
if ($null -ne $exclP -and $null -ne $exclP.Value) {
    $excl = @($tj.https_gate_exclusions | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
    $httpsGateDomains = @($httpsGateDomains | Where-Object { $excl -notcontains $_ })
}
$domains = @($tj.domains | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
$ext = $tj.PSObject.Properties['external_fqdns']
if ($null -ne $ext -and $null -ne $ext.Value) {
    $domains += @($tj.external_fqdns | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
}
if ($domains.Count -eq 0) { throw "No domains in targets JSON." }

$probeScript = Join-Path $PSScriptRoot "run_hostinger_exit_monitor_probe.ps1"
$healthScript = Join-Path $PSScriptRoot "Invoke-CloudflareDnsHealthCheck_v1.ps1"
if (-not (Test-Path -LiteralPath $probeScript)) { throw "Missing: $probeScript" }

$probeOut = Join-Path $root "reports\hostinger_exit_monitor_probe_latest.json"
# In-process call so [string[]]$Domains binds correctly (Start-Process breaks splatting).
# HTTPS exit gate: apex list only (external API hosts may have no TLS on bare hostname).
& $probeScript -OutPath $probeOut -Domains $domains -HttpsGateDomains $httpsGateDomains
$probeExit = 0
if ($null -ne $LASTEXITCODE) { $probeExit = [int]$LASTEXITCODE }

$cfExit = $null
if (-not $SkipCloudflareHealth) {
    if (-not (Test-Path -LiteralPath $healthScript)) { throw "Missing: $healthScript" }
    $p2 = Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $healthScript
    ) -Wait -PassThru -NoNewWindow
    if ($null -ne $p2 -and $null -ne $p2.ExitCode) { $cfExit = [int]$p2.ExitCode }
}

$line = [ordered]@{
    schema                   = "hostinger_full_exit_stabilization_cycle_v1"
    generated_at_utc         = [datetime]::UtcNow.ToString("o")
    domains                  = @($domains)
    probe_exit_code          = $probeExit
    probe_report             = $probeOut
    cloudflare_health_exit   = $cfExit
    cloudflare_health_report = if ($SkipCloudflareHealth) { $null } else { (Join-Path $root "reports\cloudflare_dns_health_check_latest.json") }
}

$dir = Split-Path -Parent $LogJsonl
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
($line | ConvertTo-Json -Compress -Depth 6) | Add-Content -LiteralPath $LogJsonl -Encoding UTF8
Write-Host "Appended stabilization cycle to $LogJsonl" -ForegroundColor Green
Write-Host ($line | ConvertTo-Json -Compress)

$worst = $probeExit
if ($null -ne $cfExit -and $cfExit -gt $worst) { $worst = $cfExit }
exit $worst
