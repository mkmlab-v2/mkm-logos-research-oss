#Requires -Version 5.1
<#
.SYNOPSIS
  Hostinger exit — Phase 1: public DNS snapshot per apex and www (A, AAAA, CNAME, MX, TXT, NS).

.DESCRIPTION
  Read-only. Writes reports/hostinger_exit_dns_snapshot_latest.json (or -OutJson). Use for rollback baselines
  and cutover sheets. Domains default from scripts/data/hostinger_full_exit/monitor_targets_v1.json.

.PARAMETER TargetsJson
  JSON with .domains array of apex hostnames; optional .external_fqdns for hPanel "External domains" (leaf DNS only, no www.*).

.PARAMETER Domains
  Optional explicit apex list (overrides TargetsJson when non-empty).

.PARAMETER OutJson
  Output path (repo-relative or absolute).
#>
param(
    [string]$TargetsJson = "",
    [string[]]$Domains = @(),
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($TargetsJson)) {
    $TargetsJson = Join-Path $PSScriptRoot "data\hostinger_full_exit\monitor_targets_v1.json"
}
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $root "reports\hostinger_exit_dns_snapshot_latest.json"
}

function Get-UniqueStrings {
    param([object[]]$Items)
    @($Items | Where-Object { $_ } | ForEach-Object { [string]$_ } | Select-Object -Unique)
}

function Read-NsHosts {
    param([string]$Name)
    Get-UniqueStrings (Resolve-DnsName -Name $Name -Type NS -ErrorAction SilentlyContinue | ForEach-Object {
            $nh = $_.PSObject.Properties['NameHost']
            if ($null -ne $nh -and $null -ne $nh.Value) { [string]$nh.Value.Trim() }
        })
}

function Read-ARecords {
    param([string]$Name)
    Get-UniqueStrings (Resolve-DnsName -Name $Name -Type A -ErrorAction SilentlyContinue | ForEach-Object {
            $ip = $_.PSObject.Properties['IPAddress']
            if ($null -ne $ip -and $null -ne $ip.Value) { [string]$ip.Value }
        })
}

function Read-AaaaRecords {
    param([string]$Name)
    Get-UniqueStrings (Resolve-DnsName -Name $Name -Type AAAA -ErrorAction SilentlyContinue | ForEach-Object {
            $ip = $_.PSObject.Properties['IPAddress']
            if ($null -ne $ip -and $null -ne $ip.Value) { [string]$ip.Value }
        })
}

function Read-CnameTargets {
    param([string]$Name)
    Get-UniqueStrings (Resolve-DnsName -Name $Name -Type CNAME -ErrorAction SilentlyContinue | ForEach-Object {
            $nh = $_.PSObject.Properties['NameHost']
            if ($null -ne $nh -and $null -ne $nh.Value) { [string]$nh.Value.TrimEnd('.') }
        })
}

function Read-MxRecords {
    param([string]$Name)
    @(Resolve-DnsName -Name $Name -Type MX -ErrorAction SilentlyContinue | ForEach-Object {
            $pref = $_.PSObject.Properties['Preference']
            $ex = $_.PSObject.Properties['NameExchange']
            $p = if ($null -ne $pref -and $null -ne $pref.Value) { [string]$pref.Value } else { "" }
            $e = if ($null -ne $ex -and $null -ne $ex.Value) { [string]$ex.Value.TrimEnd('.') } else { "" }
            if ($e) { "$p $e" }
        } | Where-Object { $_ } | Select-Object -Unique)
}

function Read-TxtRecords {
    param([string]$Name)
    Get-UniqueStrings (Resolve-DnsName -Name $Name -Type TXT -ErrorAction SilentlyContinue | ForEach-Object {
            $st = $_.PSObject.Properties['Strings']
            if ($null -ne $st -and $null -ne $st.Value) { (@($st.Value) -join "") }
        })
}

function Build-NodeSnapshot {
    param([string]$Fqdn, [ValidateSet("apex", "www")][string]$Kind)
    $node = [ordered]@{
        fqdn  = $Fqdn
        ns    = @()
        a     = @()
        aaaa  = @()
        cname = @()
        mx    = @()
        txt   = @()
    }
    if ($Kind -eq "apex") {
        $node.ns = Read-NsHosts $Fqdn
        $node.mx = Read-MxRecords $Fqdn
        $node.txt = Read-TxtRecords $Fqdn
    }
    $node.a = Read-ARecords $Fqdn
    $node.aaaa = Read-AaaaRecords $Fqdn
    $node.cname = Read-CnameTargets $Fqdn
    return [pscustomobject]$node
}

$list = @()
$externList = @()
if ($null -ne $Domains -and $Domains.Count -gt 0) {
    $list = @($Domains | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
}
else {
    if (-not (Test-Path -LiteralPath $TargetsJson)) { throw "Missing: $TargetsJson" }
    $tj = Get-Content -LiteralPath $TargetsJson -Raw -Encoding UTF8 | ConvertFrom-Json
    $list = @($tj.domains | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
    $p = $tj.PSObject.Properties['external_fqdns']
    if ($null -ne $p -and $null -ne $p.Value) {
        $externList = @($tj.external_fqdns | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
    }
}
if ($list.Count -eq 0) { throw "No domains to snapshot." }

$byApex = [ordered]@{}
foreach ($apex in $list) {
    $www = "www.$apex"
    $byApex[$apex] = [ordered]@{
        apex = (Build-NodeSnapshot -Fqdn $apex -Kind "apex")
        www  = (Build-NodeSnapshot -Fqdn $www -Kind "www")
    }
}
foreach ($fq in $externList) {
    # Leaf: A/AAAA/CNAME only (Kind www omits NS/MX/TXT on parent zone semantics).
    $byApex[$fq] = [ordered]@{
        external_fqdn = $true
        leaf          = (Build-NodeSnapshot -Fqdn $fq -Kind "www")
    }
}

$payload = [ordered]@{
    schema                    = "hostinger_exit_dns_snapshot_v1"
    generated_at_utc          = [datetime]::UtcNow.ToString("o")
    targets_source            = if ($Domains.Count -gt 0) { "parameter" } else { $TargetsJson }
    apex_domain_count         = $list.Count
    external_fqdn_count       = $externList.Count
    domains                   = [pscustomobject]$byApex
}

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
($payload | ConvertTo-Json -Depth 12) | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Host "Wrote $OutJson" -ForegroundColor Green

exit 0
