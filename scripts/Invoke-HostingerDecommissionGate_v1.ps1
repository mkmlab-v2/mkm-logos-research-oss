#Requires -Version 5.1
<#
.SYNOPSIS
  Hostinger decommission pre-flight gate (read-only checks + prior stabilization evidence).

.PARAMETER MinStabilizationCycles
  Minimum lines in hostinger_full_exit_stabilization_log.jsonl required (0 = skip).

.PARAMETER IncludeDuplicateAudit
  Run Invoke-CloudflareDnsAuditDuplicateNames_v1.ps1 (informational; does not fail gate on dupes).

.PARAMETER OutJson
  Gate report path.
#>
param(
    [int]$MinStabilizationCycles = 0,
    [switch]$IncludeDuplicateAudit,
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $root "reports\hostinger_decommission_gate_latest.json"
}

$targetsPath = Join-Path $PSScriptRoot "data\hostinger_full_exit\monitor_targets_v1.json"
$tj = Get-Content -LiteralPath $targetsPath -Raw -Encoding UTF8 | ConvertFrom-Json
$apexMxList = @($tj.domains | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
$gateExclusions = @()
$exclP = $tj.PSObject.Properties['https_gate_exclusions']
if ($null -ne $exclP -and $null -ne $exclP.Value) {
    $gateExclusions = @($tj.https_gate_exclusions | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
}
$httpsGateApex = @($apexMxList | Where-Object { $gateExclusions -notcontains $_ })
$domains = @($apexMxList)
$ext = $tj.PSObject.Properties['external_fqdns']
if ($null -ne $ext -and $null -ne $ext.Value) {
    $domains += @($tj.external_fqdns | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
}

$gates = [ordered]@{
    stabilization_log_ok = $true
    cloudflare_health_ok = $false
    http_dns_probe_ok    = $false
    mx_present_all       = $false
    duplicate_audit_ok   = $true
}

$logPath = Join-Path $root "reports\hostinger_full_exit_stabilization_log.jsonl"
if ($MinStabilizationCycles -gt 0) {
    if (-not (Test-Path -LiteralPath $logPath)) {
        $gates.stabilization_log_ok = $false
    }
    else {
        $n = (Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue | Where-Object { $_.Trim().Length -gt 0 }).Count
        $gates.stabilization_log_ok = ($n -ge $MinStabilizationCycles)
    }
}

$healthScript = Join-Path $PSScriptRoot "Invoke-CloudflareDnsHealthCheck_v1.ps1"
$p = Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $healthScript
) -Wait -PassThru -NoNewWindow
$hExit = 99
if ($null -ne $p -and $null -ne $p.ExitCode) { $hExit = [int]$p.ExitCode }
$gates.cloudflare_health_ok = ($hExit -eq 0)
$healthPath = Join-Path $root "reports\cloudflare_dns_health_check_latest.json"
$healthOverall = $false
if (Test-Path -LiteralPath $healthPath) {
    $hj = Get-Content -LiteralPath $healthPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $healthOverall = [bool]$hj.overall_ok
}

$probeScript = Join-Path $PSScriptRoot "run_hostinger_exit_monitor_probe.ps1"
$probeOut = Join-Path $root "reports\hostinger_exit_monitor_probe_latest.json"
& $probeScript -OutPath $probeOut -Domains $domains -HttpsGateDomains $httpsGateApex
$pe = 0
if ($null -ne $LASTEXITCODE) { $pe = [int]$LASTEXITCODE }
$gates.http_dns_probe_ok = ($pe -eq 0)
if (Test-Path -LiteralPath $probeOut) {
    $pj = Get-Content -LiteralPath $probeOut -Raw -Encoding UTF8 | ConvertFrom-Json
    $bad = @($pj.results | Where-Object {
            $gd = $_.domain.ToString()
            ($httpsGateApex | ForEach-Object { $_.ToString() }) -contains $gd -and -not $_.ok
        }).Count
    $gates.http_dns_probe_ok = ($gates.http_dns_probe_ok -and ($bad -eq 0))
}

$mxOk = $true
foreach ($d in $apexMxList) {
    if ($gateExclusions -contains $d) { continue }
    $mx = @(Resolve-DnsName -Name $d -Type MX -ErrorAction SilentlyContinue)
    if ($mx.Count -lt 1) { $mxOk = $false; break }
}
$gates.mx_present_all = $mxOk

if ($IncludeDuplicateAudit) {
    $aud = Join-Path $PSScriptRoot "Invoke-CloudflareDnsAuditDuplicateNames_v1.ps1"
    $zoneArg = ($apexMxList -join ',')
    $p3 = Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $aud, "-ZoneNames", $zoneArg
    ) -Wait -PassThru -NoNewWindow
    if ($null -eq $p3 -or $p3.ExitCode -ne 0) { $gates.duplicate_audit_ok = $false }
}

$go = [bool](
    $gates.stabilization_log_ok -and
    $gates.cloudflare_health_ok -and
    $healthOverall -and
    $gates.http_dns_probe_ok -and
    $gates.mx_present_all -and
    $gates.duplicate_audit_ok
)

$payload = [ordered]@{
    schema                   = "hostinger_decommission_gate_v1"
    generated_at_utc         = [datetime]::UtcNow.ToString("o")
    min_stabilization_cycles = $MinStabilizationCycles
    gates                    = [pscustomobject]$gates
    health_overall_ok        = $healthOverall
    go                       = $go
    note                     = "Human: confirm Business Web Hosting backup + hPanel cancellation after GO. VPS stays."
}

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
($payload | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Host "Wrote $OutJson" -ForegroundColor Green
Write-Host ($payload | ConvertTo-Json -Compress)

if (-not $go) { exit 1 }
exit 0
