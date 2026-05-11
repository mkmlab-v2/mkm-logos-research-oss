#Requires -Version 5.1
<#
.SYNOPSIS
  Prophecy evolution + B-track hit-rate eval staleness watchdog (deterministic JSON + exit code).

.DESCRIPTION
  Runs scripts/check_prophecy_evolution_watchdog_v1.py. On failure (exit 1), optional webhook:
  PROPHECY_EVOLUTION_WATCHDOG_WEBHOOK_URL, else OPS_ALARM_WEBHOOK_URL.
  -BundleMode: allow missing ablation/hit-rate files (staleness still enforced when present).
  Optional hit-rate tail JSONL (deduped by eval generated_at_utc) + streak/EMA guards via py flags.

.EXAMPLE
  py scripts/check_prophecy_evolution_watchdog_v1.py --workspace-root C:\workspace

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "...\Invoke-ProphecyEvolutionWatchdog_v1.ps1" -BundleMode
#>
param(
    [string]$WorkspaceRoot = "",
    [switch]$BundleMode,
    [double]$MaxAblationAgeHours = 96,
    [double]$MaxHitRateAgeHours = 96,
    [int]$HitRateStreakCount = 0,
    [double]$HitRateStreakBelow = 0.40,
    [Nullable[double]]$HitRateEmaMin = $null,
    [double]$HitRateEmaAlpha = 0.25,
    [int]$HitRateEmaMaxLines = 48,
    [string]$OutJson = "",
    [switch]$SkipWebhook
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
Set-Location -LiteralPath $WorkspaceRoot

$py = Join-Path $env:WINDIR "py.exe"
if (-not (Test-Path -LiteralPath $py)) {
    $py = (Get-Command -Name "py" -ErrorAction Stop).Source
}

$scriptPath = Join-Path $WorkspaceRoot "scripts\check_prophecy_evolution_watchdog_v1.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$out = $OutJson.Trim()
if ([string]::IsNullOrWhiteSpace($out)) {
    $out = Join-Path $WorkspaceRoot "reports\prophecy_evolution_watchdog_latest.json"
}

$args = @(
    $scriptPath,
    "--workspace-root", $WorkspaceRoot,
    "--out-json", $out,
    "--max-ablation-age-hours", "$MaxAblationAgeHours",
    "--max-hit-rate-age-hours", "$MaxHitRateAgeHours"
)
if ($BundleMode) {
    $args += "--allow-missing-ablation"
    $args += "--allow-missing-hit-rate"
}

if ($HitRateStreakCount -gt 0) {
    $args += "--hit-rate-streak-count"
    $args += "$HitRateStreakCount"
    $args += "--hit-rate-streak-below"
    $args += "$HitRateStreakBelow"
}

if ($null -ne $HitRateEmaMin) {
    $args += "--hit-rate-ema-min"
    $args += "$HitRateEmaMin"
    $args += "--hit-rate-ema-alpha"
    $args += "$HitRateEmaAlpha"
    $args += "--hit-rate-ema-max-lines"
    $args += "$HitRateEmaMaxLines"
}

& $py @args
$code = [int]$LASTEXITCODE

if ($code -ne 0 -and -not $SkipWebhook) {
    $webhook = $env:PROPHECY_EVOLUTION_WATCHDOG_WEBHOOK_URL
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:OPS_ALARM_WEBHOOK_URL
    }
    if (-not [string]::IsNullOrWhiteSpace($webhook)) {
        $raw = Get-Content -LiteralPath $out -Raw -ErrorAction SilentlyContinue
        $summary = $null
        if ($raw) {
            try { $summary = $raw | ConvertFrom-Json } catch { $summary = @{ parse_error = $_.Exception.Message; raw = $raw } }
        }
        $payload = [ordered]@{
            event = "prophecy_evolution_watchdog_failed"
            ts_utc = (Get-Date).ToUniversalTime().ToString("o")
            workspace = $WorkspaceRoot
            bundle_mode = [bool]$BundleMode
            exit_code = $code
            report_path = $out
            summary = $summary
        }
        $body = $payload | ConvertTo-Json -Depth 12 -Compress
        try {
            $null = Invoke-RestMethod -Uri $webhook -Method Post -Body $body -ContentType "application/json; charset=utf-8" -TimeoutSec 30
            Write-Host "Webhook alert sent: prophecy_evolution_watchdog_failed" -ForegroundColor Yellow
        }
        catch {
            Write-Warning "Webhook alert failed: $($_.Exception.Message)"
        }
    }
}

exit $code
