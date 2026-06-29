#Requires -Version 5.1
<#
.SYNOPSIS
  PersonaDiary 원클릭 자동 운영: CF 프로브 → (가능 시) DNS → 갱신·빌드·배포 → 라이브 스모크.

.EXAMPLE
  powershell -File scripts\Invoke-PersonadiaryLiveOpsAuto_v1.ps1 -Deploy

.EXAMPLE
  powershell -File scripts\Invoke-PersonadiaryLiveOpsAuto_v1.ps1 -SmokeOnly
#>
param(
    [switch]$Deploy,
    [switch]$SmokeOnly,
    [switch]$SkipDns
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$steps = @{}

function Step($Name, [scriptblock]$Block) {
    try {
        & $Block
        $script:steps[$Name] = @{ ok = ($LASTEXITCODE -eq 0); exit = $LASTEXITCODE }
    }
    catch {
        $script:steps[$Name] = @{ ok = $false; error = $_.Exception.Message }
    }
}

Step "cf_token_probe" {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\Invoke-PersonadiaryCloudflareTokenProbe_v1.ps1"
}
$dnsCapable = ($steps["cf_token_probe"].ok -eq $true)

if (-not $SmokeOnly) {
    if ($dnsCapable -and -not $SkipDns) {
        Step "preview_dns_apply" {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\Invoke-PersonadiaryPreviewDnsEnsure_v1.ps1" -Apply
        }
        Step "routing_readiness_apply" {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\Invoke-PersonadiaryCloudflareRoutingReadiness_v1.ps1" -Apply
        }
    }
    else {
        $steps["preview_dns_apply"] = @{ ok = $false; skipped = "dns_token_scope_or_SkipDns"; exit = 77 }
        $steps["routing_readiness_apply"] = @{ ok = $false; skipped = "dns_token_scope_or_SkipDns"; exit = 77 }
    }

    $bundleArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", "scripts\Invoke-PersonadiaryParallelBundle_v1.ps1",
        "-SkipPreviewDns"
    )
    if ($Deploy) { $bundleArgs += "-Deploy" }
    Step "parallel_bundle" {
        & powershell.exe @bundleArgs
    }
}

Step "live_ops_smoke" {
    & py scripts\run_personadiary_live_ops_smoke_v1.py
}

Step "subroutes_smoke" {
    Push-Location (Join-Path $root "projects\no1kmedi")
    node scripts\check-no1kmedi-subroutes-smoke_v1.mjs
    Pop-Location
}

$coreOk = @("live_ops_smoke")
if (-not $SmokeOnly) { $coreOk += "parallel_bundle" }
$corePassed = -not ($coreOk | ForEach-Object { $steps[$_] } | Where-Object { $_.ok -eq $false })

$out = Join-Path $root "reports\personadiary_live_ops_auto_latest.json"
@{
    schema           = "personadiary_live_ops_auto_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    deploy           = [bool]$Deploy
    smoke_only       = [bool]$SmokeOnly
    dns_capable      = $dnsCapable
    steps            = $steps
    ok               = $corePassed
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $out -Encoding UTF8

Write-Host "Wrote $out"
$steps.GetEnumerator() | ForEach-Object { Write-Host "$($_.Key) ok=$($_.Value.ok)" }
exit $(if ($corePassed) { 0 } else { 1 })
