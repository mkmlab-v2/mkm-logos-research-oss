#Requires -Version 5.1
<#
.SYNOPSIS
  personadiary.com Cloudflare DNS/routing readiness runner (default: dry-run).

.DESCRIPTION
  Reuses Invoke-JemaaiCloudCloudflareDnsEnsure_v1.ps1 to ensure `www.personadiary.com -> personadiary.com`
  and writes an operational readiness report.

  Default mode is WhatIf (no DNS mutation). Pass -Apply to run actual DNS create/patch.

.PARAMETER Apply
  If set, perform real DNS action (create/patch). Otherwise dry-run only.

.PARAMETER AllowDeleteConflictingWwwHost
  Passed through to DNS ensure script (destructive for conflicting A/AAAA at www host).

.PARAMETER OutJson
  Report path. Default: reports/personadiary_cloudflare_routing_readiness_latest.json
#>
param(
    [switch]$Apply,
    [switch]$AllowDeleteConflictingWwwHost,
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $root "reports\personadiary_cloudflare_routing_readiness_latest.json"
}

$fixturePath = Join-Path $root "scripts\data\hostinger_full_exit\personadiary_cloudflare_zone_v1.json"
$ensureScript = Join-Path $PSScriptRoot "Invoke-JemaaiCloudCloudflareDnsEnsure_v1.ps1"
$ensureOut = Join-Path $root "reports\cloudflare_dns_ensure_personadiary_com.json"

$report = [ordered]@{
    schema = "personadiary_cloudflare_routing_readiness_v1"
    generated_at_utc = [datetime]::UtcNow.ToString("o")
    mode = if ($Apply) { "apply" } else { "dry_run" }
    zone_name = "personadiary.com"
    fixture = [ordered]@{
        path = $fixturePath
        exists = (Test-Path -LiteralPath $fixturePath)
        zone_id = $null
    }
    dns_ensure = [ordered]@{
        script = $ensureScript
        out_json = $ensureOut
        exit_code = $null
        ran_with_apply = [bool]$Apply
    }
    web_routing_stub = [ordered]@{
        middleware_path = "projects/no1kmedi/src/middleware.ts"
        expected_hosts = @("personadiary.com", "www.personadiary.com", "preview.personadiary.com")
        expected_rewrite = "/ -> /personadiary"
    }
    next_steps = @(
        "1) Verify Cloudflare token scope (Zone.DNS:Read/Edit) before apply.",
        "2) If apply mode succeeds, confirm www CNAME in Cloudflare dashboard.",
        "3) Route personadiary.com host to no1kmedi deployment and validate /personadiary render.",
        "4) Keep legal/copy guardrails before public launch."
    )
    ok = $false
}

if ($report.fixture.exists) {
    try {
        $fixture = Get-Content -LiteralPath $fixturePath -Raw | ConvertFrom-Json
        if ($fixture -and $fixture.zone_id) {
            $report.fixture.zone_id = [string]$fixture.zone_id
        }
    }
    catch {
        $report.fixture.parse_error = "$($_.Exception.Message)"
    }
}

$argList = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", $ensureScript,
    "-ZoneName", "personadiary.com",
    "-OutJson", $ensureOut
)
if (-not $Apply) {
    $argList += "-WhatIf"
}
if ($AllowDeleteConflictingWwwHost) {
    $argList += "-AllowDeleteConflictingWwwHost"
}

$proc = Start-Process -FilePath "powershell.exe" -ArgumentList $argList -Wait -PassThru -NoNewWindow
$code = if ($null -ne $proc -and $null -ne $proc.ExitCode) { [int]$proc.ExitCode } else { 99 }
$report.dns_ensure.exit_code = $code

$report.ok = ($code -eq 0 -and $report.fixture.exists)

$outDir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
($report | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Host "Wrote $OutJson" -ForegroundColor Green
Write-Host ($report | ConvertTo-Json -Compress)

exit $(if ($report.ok) { 0 } else { 1 })

