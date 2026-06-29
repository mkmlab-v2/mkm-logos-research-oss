<#
.SYNOPSIS
  Weekly read-only watch: Gmail u/1 + Phoenix benefits + partner console probes (CDP 9222).

.DESCRIPTION
  Observation-only — no GPU, no form submit, no live trade.
  Requires NvidiaInceptionAutofillChrome on port 9222 (sessions may expire between runs).
#>
param(
    [string]$WorkspaceRoot = "",
    [switch]$SkipCdpBootstrap,
    [switch]$SkipGmail,
    [switch]$SkipPhoenix,
    [switch]$SkipPartnerChain,
    [switch]$SkipAzureReadonly
)

$ErrorActionPreference = "Stop"

$resolvedRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
} elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

Set-Location -LiteralPath $resolvedRoot

function Test-CdpUp {
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:9222/json/version" -UseBasicParsing -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

$steps = [ordered]@{}
$watchOk = $true
$cdpUp = Test-CdpUp

if (-not $cdpUp -and -not $SkipCdpBootstrap) {
    $bootstrap = Join-Path $resolvedRoot "scripts\Start-ChromeForNvidiaInceptionCdp_v1.ps1"
    if (Test-Path -LiteralPath $bootstrap) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $bootstrap
        $bootRc = $LASTEXITCODE
        if ($null -eq $bootRc) { $bootRc = 0 }
        $steps["cdp_bootstrap"] = @{ exit_code = $bootRc; note = "Start-ChromeForNvidiaInceptionCdp_v1" }
        Start-Sleep -Seconds 3
        $cdpUp = Test-CdpUp
    }
}

function Invoke-WatchStep {
    param(
        [string]$Name,
        [scriptblock]$Block,
        [switch]$NonFatal,
        [switch]$SkipIfNoCdp
    )
    if ($SkipIfNoCdp -and -not $script:cdpUp) {
        $script:steps[$Name] = @{ exit_code = 77; skipped = "cdp_not_ready"; non_fatal = $true }
        return 77
    }
    & $Block
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    $script:steps[$Name] = @{ exit_code = $code; non_fatal = [bool]$NonFatal }
    if ($code -ne 0 -and -not $NonFatal) { $script:watchOk = $false }
    return $code
}

if (-not $SkipGmail) {
    Invoke-WatchStep "gmail_inception_search" {
        py scripts\gmail_inception_search_by_mail_index_v1.py --mail-index 1
    } -NonFatal -SkipIfNoCdp | Out-Null
}

if (-not $SkipPhoenix) {
    Invoke-WatchStep "phoenix_portal_snapshot" {
        py scripts\nvidia_phoenix_portal_snapshot_v1.py --cdp-url http://127.0.0.1:9222
    } -NonFatal -SkipIfNoCdp | Out-Null
}

if (-not $SkipPartnerChain) {
    Invoke-WatchStep "partner_credit_auto_chain" {
        py scripts\nvidia_partner_credit_auto_chain_v1.py
    } -NonFatal -SkipIfNoCdp | Out-Null
}

if (-not $SkipAzureReadonly) {
    Invoke-WatchStep "azure_readonly_probe" {
        py scripts\nvidia_azure_readonly_probe_v1.py
    } -NonFatal -SkipIfNoCdp | Out-Null
}

$summary = $null
$chainPath = Join-Path $resolvedRoot "reports\nvidia_partner_credit_auto_chain_latest.json"
if (Test-Path -LiteralPath $chainPath) {
    try {
        $summary = (Get-Content -LiteralPath $chainPath -Raw -Encoding UTF8 | ConvertFrom-Json).summary
    } catch {
        $summary = $null
    }
}

$phoenixLoggedIn = $null
$phoenixPath = Join-Path $resolvedRoot "reports\nvidia_phoenix_portal_live_latest.json"
if (Test-Path -LiteralPath $phoenixPath) {
    try {
        $phoenixLoggedIn = @(
            (Get-Content -LiteralPath $phoenixPath -Raw -Encoding UTF8 | ConvertFrom-Json).pages |
            ForEach-Object { $_.logged_in }
        )
    } catch {
        $phoenixLoggedIn = $null
    }
}

$report = [ordered]@{
    schema = "nvidia_inception_partner_credit_weekly_watch_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    cdp_up = $cdpUp
    ok = $watchOk
    steps = $steps
    partner_chain_summary = $summary
    phoenix_logged_in_per_page = $phoenixLoggedIn
    artifacts = [ordered]@{
        partner_chain = "reports/nvidia_partner_credit_auto_chain_latest.json"
        phoenix_live = "reports/nvidia_phoenix_portal_live_latest.json"
        gmail_search = "reports/gmail_moksorinw_inception_search_latest.json"
        azure_readonly = "reports/nvidia_azure_readonly_probe_latest.json"
        routing_ssot = "reports/nvidia_inception_email_credit_routing_ssot_v1_latest.json"
    }
    operator_note_ko = "Weekly observation only. CDP session expired => skip code 77. No auto credit trigger."
}

$outLatest = Join-Path $resolvedRoot "reports\nvidia_inception_partner_credit_weekly_watch_latest.json"
$logJsonl = Join-Path $resolvedRoot "reports\nvidia_inception_partner_credit_weekly_watch_log.jsonl"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($outLatest, (($report | ConvertTo-Json -Depth 8) + "`n"), $utf8NoBom)

$logLine = ($report | ConvertTo-Json -Depth 6 -Compress)
Add-Content -LiteralPath $logJsonl -Value $logLine -Encoding UTF8

Write-Host "WROTE: $outLatest"
Write-Host "APPEND: $logJsonl"
Write-Host "NVIDIA_INCEPTION_WEEKLY_WATCH_OK=$watchOk CDP_UP=$cdpUp"

if (-not $watchOk) { exit 1 }
exit 0
