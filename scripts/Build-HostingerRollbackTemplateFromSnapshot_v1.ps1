#Requires -Version 5.1
<#
.SYNOPSIS
  Build rollback_dns-style template from latest DNS snapshot (derived artifact; safe to regenerate).

.DESCRIPTION
  Reads reports/hostinger_exit_dns_snapshot_latest.json (Invoke-HostingerExitDnsSnapshot_v1.ps1 output).
  For each apex: apex_a = first public A; apex_a_list = all unique A from snapshot; same pattern for www CNAME lists.
  Writes scripts/data/hostinger_full_exit/rollback_dns_template_from_snapshot_v1.json — does not overwrite
  the hand-edited rollback_dns_template_v1.json unless -OutJson points there.

.PARAMETER SnapshotJson
  Path to snapshot JSON.

.PARAMETER OutJson
  Output template path.
#>
param(
    [string]$SnapshotJson = "",
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($SnapshotJson)) {
    $SnapshotJson = Join-Path $root "reports\hostinger_exit_dns_snapshot_latest.json"
}
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $PSScriptRoot "data\hostinger_full_exit\rollback_dns_template_from_snapshot_v1.json"
}

if (-not (Test-Path -LiteralPath $SnapshotJson)) { throw "Missing snapshot (run Invoke-HostingerExitDnsSnapshot_v1.ps1 first): $SnapshotJson" }
$snap = Get-Content -LiteralPath $SnapshotJson -Raw -Encoding UTF8 | ConvertFrom-Json
if ($null -eq $snap.domains) { throw "Snapshot missing .domains" }

$domainsOut = [ordered]@{}
foreach ($prop in $snap.domains.PSObject.Properties) {
    $apex = [string]$prop.Name
    $bundle = $prop.Value
    if ($null -eq $bundle) { continue }
    $extFlag = $bundle.PSObject.Properties['external_fqdn']
    if ($null -ne $extFlag -and $null -ne $extFlag.Value -and [bool]$extFlag.Value) {
        continue
    }
    $aApex = @($bundle.apex.a)
    $cWww = @($bundle.www.cname)
    $apexList = @(
        $aApex | ForEach-Object {
            $s = [string]$_
            if (-not [string]::IsNullOrWhiteSpace($s)) { $s.Trim() }
        } | Where-Object { $_ } | Select-Object -Unique | Sort-Object
    )
    $apex_a = ""
    if ($apexList.Count -gt 0) { $apex_a = [string]$apexList[0] }
    $wwwList = @(
        $cWww | ForEach-Object {
            $s = [string]$_
            if (-not [string]::IsNullOrWhiteSpace($s)) { $s.Trim().TrimEnd('.') }
        } | Where-Object { $_ } | Select-Object -Unique | Sort-Object
    )
    $wwwC = ""
    if ($wwwList.Count -gt 0) { $wwwC = [string]$wwwList[0] }
    $domainsOut[$apex] = [ordered]@{
        apex_a           = $apex_a
        apex_a_list      = @($apexList)
        www_cname_target = $wwwC
        www_cname_list   = @($wwwList)
    }
}

$payload = [ordered]@{
    schema           = "hostinger_exit_rollback_dns_template_from_snapshot_v1"
    generated_at_utc = [datetime]::UtcNow.ToString("o")
    snapshot_source  = $SnapshotJson
    note             = "Auto-generated from public DNS snapshot; review before using as rollback authority."
    domains          = [pscustomobject]$domainsOut
}

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
($payload | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Host "Wrote $OutJson" -ForegroundColor Green

exit 0
