#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot Cloudflare DNS health: token verify + optional ensure chain + HTTPS HEAD probes.

.DESCRIPTION
  Runs Invoke-CloudflareApiTokenVerify_v1.ps1, then Run-CloudflareDnsEnsureChain_v1.ps1 (default: no destructive www A delete).
  Writes reports/cloudflare_dns_health_check_latest.json and exits non-zero if any gate fails.

.PARAMETER ZoneNames
  Comma-separated apex zones (default jema-ai.com,no1kmedi.com,jemaai.cloud). Passed to DNS ensure chain.

.PARAMETER ChainAllowDeleteConflictingWwwHost
  Pass through to Run-CloudflareDnsEnsureChain_v1.ps1 (destructive; off by default for weekly health).

.PARAMETER SkipDnsEnsureChain
  Only run token verify + HTTPS.

.PARAMETER SkipHttpsHead
  Skip HTTP(S) probes.

.PARAMETER HttpsUrls
  URLs for HEAD (default: jemaai.cloud apex + www).

.PARAMETER OutJson
  Summary path (default reports/cloudflare_dns_health_check_latest.json).

.PARAMETER WeeklyHttpsPrimary
  Weekly solo monitor: pass when token active + zones visible + HTTPS OK even if DNS list API returns 403 (tunnel-scoped token). Skips DNS ensure chain.

.NOTES
  Requires CLOUDFLARE_API_TOKEN or CF_API_TOKEN (User env preferred; see other Cloudflare scripts).
  Full DNS mutate path: docs/research/raw/cloudflare_dns_weekly_token_scope_v1.md
#>
param(
    [string]$ZoneNames = "jema-ai.com,no1kmedi.com,jemaai.cloud",
    [switch]$ChainAllowDeleteConflictingWwwHost,
    [switch]$SkipDnsEnsureChain,
    [switch]$SkipHttpsHead,
    [switch]$WeeklyHttpsPrimary,
    [string[]]$HttpsUrls = @("https://jemaai.cloud/", "https://www.jemaai.cloud/"),
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $root "reports\cloudflare_dns_health_check_latest.json"
}

$verifyScript = Join-Path $PSScriptRoot "Invoke-CloudflareApiTokenVerify_v1.ps1"
$chainScript  = Join-Path $PSScriptRoot "Run-CloudflareDnsEnsureChain_v1.ps1"

if (-not (Test-Path -LiteralPath $verifyScript)) { throw "Missing: $verifyScript" }
if (-not (Test-Path -LiteralPath $chainScript)) { throw "Missing: $chainScript" }

if ($WeeklyHttpsPrimary) {
    $SkipDnsEnsureChain = $true
}

$out = [ordered]@{
    schema           = "cloudflare_dns_health_check_v1"
    generated_at_utc = ""
    zone_names       = $ZoneNames.Trim()
    weekly_https_primary = [bool]$WeeklyHttpsPrimary
    verify           = @{ exit_code = $null; report = (Join-Path $root "reports\cloudflare_api_token_verify_latest.json") }
    chain            = @{ skipped = [bool]$SkipDnsEnsureChain; exit_code = $null; report = (Join-Path $root "reports\cloudflare_dns_ensure_chain_latest.json") }
    https            = @()
    gates            = [ordered]@{
        verify_token_active  = $false
        verify_all_probes_ok = $false
        dns_api_read_ok      = $false
        chain_ok             = $false
        https_all_ok         = $false
    }
    degraded         = $false
    degraded_reason  = $null
    overall_ok       = $false
}

& $verifyScript
$out.verify.exit_code = 0

$vpath = $out.verify.report
if (-not (Test-Path -LiteralPath $vpath)) { throw "Verify report missing: $vpath" }
$vj = Get-Content -LiteralPath $vpath -Raw -Encoding UTF8 | ConvertFrom-Json
$zonesOk = $true
$dnsReadOk = $true
foreach ($p in @($vj.dns_probes)) {
    if (-not $p.zone_found) { $zonesOk = $false }
    if (-not $p.dns_list_ok) { $dnsReadOk = $false }
}
$tokenActive = ([string]$vj.status -eq "active")
$out.gates.verify_token_active = $tokenActive
$out.gates.dns_api_read_ok = $dnsReadOk
if ($WeeklyHttpsPrimary) {
    $out.gates.verify_all_probes_ok = ($tokenActive -and $zonesOk)
    if (-not $dnsReadOk) {
        $out.degraded = $true
        $out.degraded_reason = "dns_list_403_tunnel_token_weekly_https_primary"
    }
}
else {
    $out.gates.verify_all_probes_ok = ($tokenActive -and $zonesOk -and $dnsReadOk)
}
if (-not $out.gates.verify_all_probes_ok) { $out.verify.exit_code = 1 }

if (-not $SkipDnsEnsureChain) {
    $argList = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $chainScript,
        "-ZoneNames", $ZoneNames.Trim()
    )
    if ($ChainAllowDeleteConflictingWwwHost) {
        $argList += "-AllowDeleteConflictingWwwHost"
    }
    $p = Start-Process -FilePath "powershell.exe" -ArgumentList $argList -Wait -PassThru -NoNewWindow
    $code = 99
    if ($null -ne $p -and $null -ne $p.ExitCode) { $code = [int]$p.ExitCode }
    $out.chain.exit_code = $code
    $out.gates.chain_ok = ($code -eq 0)
}
else {
    $out.chain.exit_code = $null
    $out.gates.chain_ok = $true
}

$httpsOk = $true
if (-not $SkipHttpsHead -and $HttpsUrls -and @($HttpsUrls).Count -gt 0) {
    foreach ($u in @($HttpsUrls)) {
        if ([string]::IsNullOrWhiteSpace($u)) { continue }
        $row = [ordered]@{ url = $u.Trim(); status_code = $null; ok = $false; error = $null }
        try {
            $r = Invoke-WebRequest -Uri $row.url -Method Head -TimeoutSec 25 -MaximumRedirection 5 -UseBasicParsing
            $row.status_code = [int]$r.StatusCode
            $row.ok = ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400)
        }
        catch {
            $row.error = $_.Exception.Message
            $row.ok = $false
            $httpsOk = $false
        }
        if (-not $row.ok) { $httpsOk = $false }
        $out.https += [pscustomobject]$row
    }
}
else {
    $out.gates.https_all_ok = $true
}

if (-not $SkipHttpsHead -and $HttpsUrls -and @($HttpsUrls).Count -gt 0) {
    $out.gates.https_all_ok = $httpsOk
}
else {
    $out.gates.https_all_ok = $true
}

$out.overall_ok = ($out.gates.verify_all_probes_ok -and $out.gates.chain_ok -and $out.gates.https_all_ok)

$out.generated_at_utc = [datetime]::UtcNow.ToString("o")

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
($out | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Host "Wrote $OutJson" -ForegroundColor Green
Write-Host ($out | ConvertTo-Json -Compress -Depth 6)

$exit = 0
if (-not $out.overall_ok) { $exit = 1 }
exit $exit
