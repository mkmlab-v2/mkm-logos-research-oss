#Requires -Version 5.1
<#
.SYNOPSIS
  personadiary parallel: build/deploy + optional preview DNS (token-gated).

.PARAMETER Deploy
  Deploy no1kmedi after local npm build.

.PARAMETER DnsApply
  Apply preview CNAME when token has Zone.DNS Edit on personadiary.com.

.PARAMETER StrictDns
  Fail bundle exit code when DNS steps fail (default: deploy/build can still pass).

.PARAMETER WaitlistEmbedUrl
  Injects NEXT_PUBLIC_PERSONADIARY_WAITLIST_EMBED_URL into projects/no1kmedi/.env.production before build.

.PARAMETER SkipPreviewDns
  Skip Cloudflare preview DNS steps entirely.
#>
param(
    [switch]$Deploy,
    [switch]$DnsApply,
    [switch]$StrictDns,
    [switch]$SkipPreviewDns,
    [string]$WaitlistEmbedUrl = ""
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$steps = @{}
$blockers = @()

function Step($Name, [scriptblock]$Block) {
    try {
        & $Block
        $script:steps[$Name] = @{ ok = ($LASTEXITCODE -eq 0); exit = $LASTEXITCODE }
    } catch {
        $script:steps[$Name] = @{ ok = $false; error = $_.Exception.Message }
    }
}

$dnsCapable = $false
if (-not $SkipPreviewDns) {
    Step "cf_token_probe" {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\Invoke-PersonadiaryCloudflareTokenProbe_v1.ps1"
    }
    $dnsCapable = ($steps["cf_token_probe"].ok -eq $true)
    if (-not $dnsCapable) {
        $blockers += @{
            id = "cloudflare_dns_scope"
            fix = "Cloudflare에서 API 토큰 생성: personadiary.com 존에 Zone.DNS Read + Zone.DNS Edit. 레포 .env에 MKM_CLOUDFLARE_PERSONADIARY_DNS_TOKEN=... 추가 후 sync_required_env_to_user.ps1"
            dashboard = "https://dash.cloudflare.com/profile/api-tokens"
        }
        $steps["preview_dns"] = @{ ok = $false; exit = 77; skipped = "token_lacks_dns_scope" }
        $steps["routing_readiness"] = @{ ok = $false; exit = 77; skipped = "token_lacks_dns_scope" }
    }
}

if ($dnsCapable -and -not $SkipPreviewDns) {
    Step "preview_dns" {
        $dnsArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\Invoke-PersonadiaryPreviewDnsEnsure_v1.ps1")
        if ($DnsApply) { $dnsArgs += "-Apply" }
        & powershell.exe @dnsArgs
    }
    Step "routing_readiness" {
        $rdArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\Invoke-PersonadiaryCloudflareRoutingReadiness_v1.ps1")
        if ($DnsApply) { $rdArgs += "-Apply" }
        & powershell.exe @rdArgs
    }
}

if (-not [string]::IsNullOrWhiteSpace($WaitlistEmbedUrl)) {
    $prodEnv = Join-Path $root "projects\no1kmedi\.env.production"
    $line = "NEXT_PUBLIC_PERSONADIARY_WAITLIST_EMBED_URL=$($WaitlistEmbedUrl.Trim())"
    $existing = @()
    if (Test-Path -LiteralPath $prodEnv) {
        $existing = Get-Content -LiteralPath $prodEnv | Where-Object {
            $_ -notmatch '^\s*NEXT_PUBLIC_PERSONADIARY_WAITLIST_EMBED_URL\s*='
        }
    }
    ($existing + $line) | Set-Content -LiteralPath $prodEnv -Encoding UTF8
    $steps["waitlist_env"] = @{ ok = $true; url_set = $true }
} else {
    $wl = [Environment]::GetEnvironmentVariable("NEXT_PUBLIC_PERSONADIARY_WAITLIST_EMBED_URL", "User")
    if ([string]::IsNullOrWhiteSpace($wl)) {
        $wl = [Environment]::GetEnvironmentVariable("NEXT_PUBLIC_PERSONADIARY_WAITLIST_EMBED_URL", "Process")
    }
    if ([string]::IsNullOrWhiteSpace($wl)) {
        $steps["waitlist_env"] = @{ ok = $true; mode = "native_api_form"; path = "/api/leads/personadiary-waitlist" }
    } else {
        $steps["waitlist_env"] = @{ ok = $true; from_env = $true; mode = "iframe_embed" }
    }
}

Step "daily_guide_refresh" {
    $dgArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\Run-PersonadiaryDailyGuideRefresh_v1.ps1", "-WorkspaceRoot", $root, "-SkipRegenerate")
    & powershell.exe @dgArgs
}

Step "npm_build" {
    Push-Location (Join-Path $root "projects\no1kmedi")
    npm run build
    Pop-Location
}

if ($Deploy) {
    Step "deploy_no1kmedi" {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\Deploy-No1kmediDestinyTarball_v1.ps1" -SkipLocalBuild
    }
}

$coreOk = @("daily_guide_refresh", "npm_build")
if ($Deploy) { $coreOk += "deploy_no1kmedi" }
$corePassed = -not ($coreOk | ForEach-Object { $steps[$_] } | Where-Object { $_.ok -eq $false })

$dnsOk = $true
if (-not $SkipPreviewDns) {
    $dnsOk = ($steps["preview_dns"].ok -eq $true) -and ($steps["routing_readiness"].ok -eq $true)
}

$overallOk = if ($StrictDns) {
    $corePassed -and $dnsOk -and (-not ($blockers.Count -gt 0))
} else {
    $corePassed
}

$out = Join-Path $root "reports\personadiary_parallel_bundle_latest.json"
@{
    schema = "personadiary_parallel_bundle_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    steps = $steps
    blockers = $blockers
    dns_capable = $dnsCapable
    strict_dns = [bool]$StrictDns
    ok = $overallOk
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $out -Encoding UTF8

if ($blockers.Count -gt 0) {
    $blockers | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $root "reports\personadiary_automation_blockers_latest.json") -Encoding UTF8
}

Write-Host "Wrote $out"
$steps.GetEnumerator() | ForEach-Object { Write-Host "$($_.Key) ok=$($_.Value.ok)" }
if ($blockers.Count -gt 0) {
    Write-Host "Blockers (manual once):" -ForegroundColor Yellow
    $blockers | ForEach-Object { Write-Host "  [$($_.id)] $($_.fix)" }
}
exit $(if ($overallOk) { 0 } else { 1 })
