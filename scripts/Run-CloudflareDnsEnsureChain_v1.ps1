#Requires -Version 5.1
<#
.SYNOPSIS
  Run Invoke-JemaaiCloudCloudflareDnsEnsure_v1.ps1 for multiple zones; one JSON summary.

.PARAMETER ZoneNames
  Default: jema-ai.com, no1kmedi.com (Cloudflare에 존이 있을 때만). jemaai.cloud 존을 추가한 뒤에는 `-ZoneNames @('jema-ai.com','no1kmedi.com','jemaai.cloud')` 등으로 확장.

.PARAMETER AllowDeleteConflictingWwwHost
  Passed through to Invoke-JemaaiCloudCloudflareDnsEnsure_v1.ps1 (deletes A/AAAA at www when needed).

.NOTES
  Per-zone report: reports/cloudflare_dns_ensure_<zonename_sanitized>.json
  Requires CLOUDFLARE_API_TOKEN or CF_API_TOKEN.
#>
param(
    [string[]]$ZoneNames = @("jema-ai.com", "no1kmedi.com"),
    [switch]$AllowDeleteConflictingWwwHost,
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "Invoke-JemaaiCloudCloudflareDnsEnsure_v1.ps1"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $root "reports\cloudflare_dns_ensure_chain_latest.json"
}

$results = [System.Collections.Generic.List[object]]::new()
$worst = 0

foreach ($z in $ZoneNames) {
    if ([string]::IsNullOrWhiteSpace($z)) { continue }
    $zt = $z.Trim()
    $safe = $zt -replace "\.", "_"
    $per = Join-Path $root "reports\cloudflare_dns_ensure_$safe.json"
    $one = [ordered]@{ zone = $zt; exit_code = 0; report = $per }
    $argList = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $scriptPath,
        "-ZoneName", $zt, "-OutJson", $per
    )
    if ($AllowDeleteConflictingWwwHost) {
        $argList += "-AllowDeleteConflictingWwwHost"
    }
    $p = Start-Process -FilePath "powershell.exe" -ArgumentList $argList -Wait -PassThru -NoNewWindow
    $code = 99
    if ($null -ne $p -and $null -ne $p.ExitCode) { $code = [int]$p.ExitCode }
    $one.exit_code = $code
    if ($code -ne 0) { $worst = 1 }
    $results.Add($one)
}

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$payload = [ordered]@{
    schema           = "cloudflare_dns_ensure_chain_v1"
    generated_at_utc = [datetime]::UtcNow.ToString("o")
    zones            = @($results)
    worst_exit       = $worst
}
($payload | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Host "Wrote $OutJson" -ForegroundColor Green
Write-Host ($payload | ConvertTo-Json -Compress)

exit $worst
