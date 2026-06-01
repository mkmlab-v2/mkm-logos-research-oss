#Requires -Version 5.1

<#

.SYNOPSIS

  no1kmedi.com DNS ops: public DNS/HTTPS is SSOT; API ensure is optional only.



.NOTES

  Default: exit 0 when public DNS live — do NOT nag for new CF DNS tokens.

  -RequireApiWrite: force API probe/ensure (record changes, new env).

  Policy: docs/final/artifacts/no1kmedi_cf_dns_ops_policy_v1.json

#>

param(

    [switch]$DryRun,

    [switch]$SkipBrowser,

    [switch]$ApplySecretIfPresent,

    [switch]$SkipPublicVerify,

    [switch]$RequireApiWrite

)



Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$summaryPath = Join-Path $root "reports\no1kmedi_cf_dns_ensure_chain_latest.json"

$policyPath = "docs/final/artifacts/no1kmedi_cf_dns_ops_policy_v1.json"

$steps = [System.Collections.Generic.List[object]]::new()



function Add-Step([string]$Name, [int]$ExitCode, [string]$Note) {

    $steps.Add([ordered]@{ step = $Name; exit_code = $ExitCode; note = $Note }) | Out-Null

}



function Write-JsonUtf8([string]$Path, [object]$Obj) {

    $json = $Obj | ConvertTo-Json -Depth 8

    [System.IO.File]::WriteAllText($Path, $json + "`n", [System.Text.UTF8Encoding]::new($false))

}



$secret = Join-Path $root "reports\cloudflare_dns_token_create_secret_LOCAL.json"

if ($ApplySecretIfPresent -and (Test-Path -LiteralPath $secret)) {

    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "Invoke-ApplyNo1kmediDnsTokenFromSecret_v1.ps1") -SecretJson $secret

    exit $LASTEXITCODE

}



$publicOk = $false

if (-not $SkipPublicVerify) {

    & py (Join-Path $root "scripts\verify_no1kmedi_public_dns_v1.py")

    Add-Step "public_dns_verify" $LASTEXITCODE $(if ($LASTEXITCODE -eq 0) { "all_ok" } else { "check_hosts" })

    $publicOk = ($LASTEXITCODE -eq 0)

}

else {

    $publicPath = Join-Path $root "reports\no1kmedi_public_dns_verify_latest.json"

    if (Test-Path -LiteralPath $publicPath) {

        $publicDoc = Get-Content -LiteralPath $publicPath -Raw | ConvertFrom-Json

        $publicOk = [bool]$publicDoc.all_ok

    }

}



if ($publicOk -and -not $RequireApiWrite) {

    $summary = [ordered]@{

        schema              = "no1kmedi_cf_dns_ensure_chain_v1"

        generated_at_utc    = (Get-Date).ToUniversalTime().ToString("o")

        dry_run             = [bool]$DryRun

        public_dns_ok       = $true

        api_dns_applied     = $false

        require_api_write   = $false

        operational_status  = "dns_live_no_token_required"

        policy_pointer      = $policyPath

        steps               = @($steps)

        human_next          = @()

        agent_note          = "Public DNS/HTTPS OK — do not ask commander to create CF DNS token unless -RequireApiWrite or record change."

    }

    Write-JsonUtf8 $summaryPath $summary

    Write-Host "no1kmedi DNS: public OK — token not required ($policyPath)" -ForegroundColor Green

    exit 0

}



$probeArgs = @()

if ($RequireApiWrite) { $probeArgs += "--require-api-write" }

& py (Join-Path $root "scripts\probe_no1kmedi_cf_dns_tokens_v1.py") @probeArgs

$probeExit = $LASTEXITCODE

Add-Step "token_probe" $probeExit $(if ($probeExit -eq 0) { "ops_ok" } else { "no_dns_write_token" })



if ($probeExit -ne 0 -and $RequireApiWrite) {

    & py (Join-Path $root "scripts\try_create_cloudflare_dns_token_v1.py")

    Add-Step "try_create_dns_token" $LASTEXITCODE $(if ($LASTEXITCODE -eq 0) { "created" } else { "parent_lacks_token_write" })

}



$cfArgs = @()

if ($DryRun) { $cfArgs += "--dry-run" }

if ($RequireApiWrite) { $cfArgs += "--require-api-write" }

& py (Join-Path $root "scripts\ensure_no1kmedi_research_clinic_cloudflare_dns_v1.py") @cfArgs

Add-Step "ensure_research_clinic" $LASTEXITCODE $(if ($DryRun) { "dry-run" } elseif ($LASTEXITCODE -eq 0) { "applied" } else { "api_fail" })



if ($DryRun) {

    & py (Join-Path $root "scripts\ensure_no1kmedi_api_cloudflare_dns_v1.py") --dry-run @($(if ($RequireApiWrite) { "--require-api-write" }))

}

else {

    $apiArgs = @()

    if ($RequireApiWrite) { $apiArgs += "--require-api-write" }

    & py (Join-Path $root "scripts\ensure_no1kmedi_api_cloudflare_dns_v1.py") @apiArgs

}

Add-Step "ensure_api" $LASTEXITCODE $(if ($DryRun) { "dry-run" } elseif ($LASTEXITCODE -eq 0) { "applied" } else { "api_fail" })



$apiAutomated = @($steps | Where-Object { $_.step -match "^ensure_" -and $_.exit_code -eq 0 }).Count -gt 0

$probeDoc = @{}

if (Test-Path -LiteralPath (Join-Path $root "reports\no1kmedi_cf_dns_token_probe_latest.json")) {

    $probeDoc = Get-Content -LiteralPath (Join-Path $root "reports\no1kmedi_cf_dns_token_probe_latest.json") -Raw | ConvertFrom-Json

}



$summary = [ordered]@{

    schema             = "no1kmedi_cf_dns_ensure_chain_v1"

    generated_at_utc   = (Get-Date).ToUniversalTime().ToString("o")

    dry_run            = [bool]$DryRun

    public_dns_ok      = $publicOk

    api_dns_applied    = $apiAutomated

    require_api_write  = [bool]$RequireApiWrite

    winner_env_key     = $probeDoc.winner_env_key

    policy_pointer     = $policyPath

    steps              = @($steps)

    human_next         = @()

}



if (-not $apiAutomated -and -not $publicOk) {

    $summary.human_next += "CF dashboard DNS manual: docs/final/artifacts/no1kmedi_subdomain_dns_manual_v1.json"

}

if (-not $apiAutomated -and $RequireApiWrite) {

    $summary.human_next += "Optional API sync only: MKM_CLOUDFLARE_NO1KMEDI_DNS_TOKEN via Invoke-ApplyNo1kmediDnsTokenFromSecret_v1.ps1 (never overwrite CLOUDFLARE_API_TOKEN)"

}



if ($publicOk -and $apiAutomated) {

    $summary.operational_status = "dns_live_api_synced"

    $exitCode = 0

}

elseif ($publicOk) {

    $summary.operational_status = "dns_live_no_token_required"

    $exitCode = 0

}

elseif ($apiAutomated) {

    $summary.operational_status = "api_synced_public_check_skipped"

    $exitCode = 0

}

else {

    $summary.operational_status = "dns_or_https_check_failed"

    $exitCode = 4

}



if (-not $SkipBrowser -and $RequireApiWrite -and -not $apiAutomated) {

    Write-Host "RequireApiWrite: open CF token UI for no1kmedi.com Zone DNS Edit" -ForegroundColor Yellow

    Start-Process "https://dash.cloudflare.com/profile/api-tokens"

}



Write-JsonUtf8 $summaryPath $summary

Write-Host "Summary: $summaryPath exit=$exitCode status=$($summary.operational_status)" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Yellow" })

exit $exitCode

