param(
    [switch]$EnforceRegistry,
    [switch]$SlackNotifyLive,
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\all_green_latest.json"
)

$ErrorActionPreference = "Stop"

$ops = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal"
$steps = @(
    @{
        name = "ensure_public_event_gateway"
        cmd = @("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $ops "ensure_public_event_gateway.ps1"), "-Strict")
    },
    @{
        name = "verify_fused_quant_pixel_runtime_health"
        cmd = @("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $ops "verify_fused_quant_pixel_runtime_health.ps1"))
    },
    @{
        name = "verify_jemaai_showroom_deploy"
        cmd = @("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $ops "verify_jemaai_showroom_deploy.ps1"), "-GatewayBaseUrl", "http://127.0.0.1:8788", "-AutoFixLocal")
    },
    @{
        name = "reconcile_automation_registry"
        cmd = @("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $ops "reconcile_automation_registry.ps1"))
    }
)

if ($EnforceRegistry) {
    $steps[-1].cmd += "-Enforce"
}

$results = @()
foreach ($s in $steps) {
    $name = [string]$s.name
    $cmd = $s.cmd
    Write-Host ("[verify-all-green] Running: {0}" -f $name)
    & $cmd[0] $cmd[1..($cmd.Length - 1)]
    $code = $LASTEXITCODE
    $results += [ordered]@{
        step = $name
        exit_code = $code
        ok = ($code -eq 0)
    }
    if ($code -ne 0) {
        Write-Host ("[verify-all-green] FAIL: {0} (exit={1})" -f $name, $code) -ForegroundColor Red
    }
}

$allOk = (@($results | Where-Object { -not $_.ok }).Count -eq 0)
$payload = [ordered]@{
    schema = "verify_all_green_v1"
    ts_utc = [DateTimeOffset]::UtcNow.ToString("o")
    enforce_registry = [bool]$EnforceRegistry
    overall_ok = $allOk
    steps = $results
}

$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
$json = $payload | ConvertTo-Json -Depth 6
Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
Write-Host $json
Write-Host ("Saved all-green report: {0}" -f $OutputPath)

# Non-fatal post-check: snapshot Slack delivery health each run.
try {
    $deliveryCheckScript = Join-Path $ops "check_all_green_slack_delivery.ps1"
    $deliveryCheckOut = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\all_green_slack_delivery_check_latest.json"
    $deliveryMaxSuccessAgeHours = 12
    if (Test-Path -LiteralPath $deliveryCheckScript) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $deliveryCheckScript -OutputPath $deliveryCheckOut -MaxSuccessAgeHours $deliveryMaxSuccessAgeHours
        if ($LASTEXITCODE -ne 0) {
            Write-Host ("[verify-all-green] WARN: delivery check unhealthy (exit={0})" -f $LASTEXITCODE) -ForegroundColor Yellow
        }
        if (Test-Path -LiteralPath $deliveryCheckOut) {
            try {
                $deliveryDoc = Get-Content -LiteralPath $deliveryCheckOut -Encoding UTF8 | ConvertFrom-Json
                if ($deliveryDoc -and $deliveryDoc.success_stale -eq $true) {
                    Write-Host (
                        "[verify-all-green] STALE_ALERT: latest successful Slack delivery is older than {0}h (age={1}h)." -f
                        $deliveryMaxSuccessAgeHours,
                        $deliveryDoc.latest_success_age_hours
                    ) -ForegroundColor Yellow
                    # Optional stale-alert Slack ping (non-fatal; follows SlackNotifyLive switch).
                    $staleAlertScript = "C:\workspace\scripts\send_all_green_stale_alert_slack.py"
                    if (Test-Path -LiteralPath $staleAlertScript) {
                        try {
                            if ([bool]$SlackNotifyLive) {
                                & py -u $staleAlertScript --input $deliveryCheckOut --live
                            } else {
                                & py -u $staleAlertScript --input $deliveryCheckOut --dry-run
                            }
                        } catch {
                            Write-Host ("[verify-all-green] WARN: stale-alert notify failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
                        }
                    } else {
                        Write-Host ("[verify-all-green] WARN: stale-alert script missing: {0}" -f $staleAlertScript) -ForegroundColor Yellow
                    }
                }
            } catch {
                Write-Host ("[verify-all-green] WARN: unable to parse delivery check snapshot: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host ("[verify-all-green] WARN: delivery check script missing: {0}" -f $deliveryCheckScript) -ForegroundColor Yellow
    }
} catch {
    Write-Host ("[verify-all-green] WARN: delivery check failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
}

if (-not $allOk) {
    # Best-effort Slack alert on failure (default is dry-run unless ALL_GREEN_SLACK_LIVE is enabled).
    try {
        $slackMaxRetries = 2
        $slackBackoffSeconds = 2
        $slackLive = [bool]$SlackNotifyLive -or (
            ($env:ALL_GREEN_SLACK_LIVE -ne $null) -and ($env:ALL_GREEN_SLACK_LIVE.ToString().ToLower() -match "^(1|true|yes|y|on)$")
        )
        $slackScript = "C:\workspace\scripts\send_all_green_failure_slack.py"
        if (Test-Path -LiteralPath $slackScript) {
            $notifyMode = if ($slackLive) { "LIVE" } else { "DRY-RUN" }
            Write-Host ("[verify-all-green] Slack notify on fail: {0}" -f $notifyMode) -ForegroundColor Yellow
            if ($slackLive) {
                & py -u $slackScript --all-green-json $OutputPath --live --max-retries $slackMaxRetries --backoff-s $slackBackoffSeconds
            } else {
                & py -u $slackScript --all-green-json $OutputPath --dry-run --max-retries $slackMaxRetries --backoff-s $slackBackoffSeconds
            }
        } else {
            Write-Host ("[verify-all-green] WARN: Slack failure script missing: {0}" -f $slackScript) -ForegroundColor Yellow
        }
    } catch {
        # Do not override the core health status; Slack failures are non-fatal for correctness.
        Write-Host ("[verify-all-green] WARN: Slack notify failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
    }

    exit 1
}
exit 0
