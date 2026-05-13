#Requires -Version 5.1
<#
.SYNOPSIS
  Registrar transfer readiness: NS delegation + tracker row completeness (read-only).

.DESCRIPTION
  Phase 4 support: loads registrar_transfer_tracker_v1.json, checks public NS for each apex contains
  'cloudflare', and booleans for lock/epp pipeline. If CLOUDFLARE_API_TOKEN or CF_API_TOKEN is set,
  also queries Cloudflare API for an active zone (helps when public NS still shows dns-parking during propagation).
  Writes reports/hostinger_registrar_transfer_readiness_latest.json

.PARAMETER TrackerJson
  Path to registrar_transfer_tracker_v1.json.

.PARAMETER OutJson
  Output path.
#>
param(
    [string]$TrackerJson = "",
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($TrackerJson)) {
    $TrackerJson = Join-Path $PSScriptRoot "data\hostinger_full_exit\registrar_transfer_tracker_v1.json"
}
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $root "reports\hostinger_registrar_transfer_readiness_latest.json"
}

if (-not (Test-Path -LiteralPath $TrackerJson)) { throw "Missing: $TrackerJson" }
$tr = Get-Content -LiteralPath $TrackerJson -Raw -Encoding UTF8 | ConvertFrom-Json

$cfTok = $null
foreach ($k in @("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN")) {
    foreach ($scope in @("User", "Machine", "Process")) {
        $v = [Environment]::GetEnvironmentVariable($k, $scope)
        if (-not [string]::IsNullOrWhiteSpace($v)) { $cfTok = $v.Trim(); break }
    }
    if ($null -ne $cfTok) { break }
}

function Test-CfZoneActive {
    param([string]$Token, [string]$ZoneName)
    if ([string]::IsNullOrWhiteSpace($Token) -or [string]::IsNullOrWhiteSpace($ZoneName)) { return $false }
    try {
        $enc = [uri]::EscapeDataString($ZoneName)
        $uri = "https://api.cloudflare.com/client/v4/zones?name=$enc&status=active"
        $h = @{ Authorization = "Bearer $Token"; "Content-Type" = "application/json" }
        $r = Invoke-RestMethod -Uri $uri -Headers $h -Method Get -MaximumRedirection 0 -ErrorAction Stop
        return ([bool]$r.success -and $null -ne $r.result -and @($r.result).Count -gt 0)
    }
    catch {
        return $false
    }
}

$rows = [System.Collections.Generic.List[object]]::new()
foreach ($d in @($tr.domains)) {
    $apex = [string]$d.apex
    $ns = @(
        Resolve-DnsName -Name $apex -Type NS -ErrorAction SilentlyContinue | ForEach-Object {
            $rec = $_
            $nh = $rec.PSObject.Properties['NameHost']
            if ($null -ne $nh -and $null -ne $nh.Value -and [string]$nh.Value.Trim().Length -gt 0) {
                [string]$nh.Value.Trim()
            }
        } | Where-Object { $_ }
    )
    $cfNs = @($ns | Where-Object { $_ -match 'cloudflare' }).Count -gt 0
    $cfZone = $false
    if ($null -ne $cfTok) { $cfZone = Test-CfZoneActive -Token $cfTok -ZoneName $apex }
    $delegOk = ($cfNs -or $cfZone)
    $rows.Add([ordered]@{
            apex                      = $apex
            ns_records                = @($ns)
            ns_includes_cloudflare    = $cfNs
            cf_active_zone_found      = $cfZone
            delegation_evidence_ok    = $delegOk
            ns_may_be_resolver_stale  = ((-not $cfNs) -and $cfZone)
            lock_released             = [bool]$d.lock_released
            epp_received              = [bool]$d.epp_received
            transfer_submitted        = [bool]$d.transfer_submitted
            transfer_completed        = [bool]$d.transfer_completed
            transfer_ready_guess      = ($delegOk -and $d.lock_released -and $d.epp_received -and -not $d.transfer_completed)
        }) | Out-Null
}

$payload = [ordered]@{
    schema                         = "hostinger_registrar_transfer_readiness_v1"
    generated_at_utc               = [datetime]::UtcNow.ToString("o")
    target_registrar               = $tr.target_registrar
    tracker_path                   = $TrackerJson
    cloudflare_api_token_used      = ($null -ne $cfTok)
    domains                        = @($rows)
    all_ns_on_cloudflare           = -not @($rows | Where-Object { -not $_.ns_includes_cloudflare }).Count
    all_delegation_evidence_ok     = -not @($rows | Where-Object { -not $_.delegation_evidence_ok }).Count
}

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
($payload | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Host "Wrote $OutJson" -ForegroundColor Green
Write-Host ($payload | ConvertTo-Json -Compress -Depth 3)

exit 0
