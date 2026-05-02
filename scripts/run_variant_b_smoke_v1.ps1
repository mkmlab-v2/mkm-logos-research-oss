param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $WorkspaceRoot "scripts\check_variant_b_smoke_v1.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Smoke script not found: $scriptPath"
}

$outDir = Join-Path $WorkspaceRoot "reports"
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir | Out-Null
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outFile = Join-Path $outDir "variant_b_smoke_${stamp}.json"
$latestFile = Join-Path $outDir "variant_b_smoke_latest.json"

$json = py $scriptPath
$exitCode = $LASTEXITCODE

$json | Out-File -LiteralPath $outFile -Encoding utf8
$json | Out-File -LiteralPath $latestFile -Encoding utf8

Write-Host "Smoke output: $outFile"
Write-Host "Latest output: $latestFile"
Write-Host "Exit code: $exitCode"

if ($exitCode -ne 0) {
    $webhook = $env:VARIANT_B_SMOKE_WEBHOOK_URL
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:OPS_ALARM_WEBHOOK_URL
    }

    if (-not [string]::IsNullOrWhiteSpace($webhook)) {
        $payload = [ordered]@{
            event       = "variant_b_smoke_alert"
            ts_utc      = (Get-Date).ToUniversalTime().ToString("o")
            workspace   = $WorkspaceRoot
            smoke_ok    = $false
            report_file = $outFile
        }

        try {
            $parsed = $json | ConvertFrom-Json
            $payload["summary"] = $parsed
        }
        catch {
            $payload["summary_parse_error"] = $_.Exception.Message
            $payload["summary_raw"] = "$json"
        }

        $body = $payload | ConvertTo-Json -Depth 12 -Compress
        try {
            $null = Invoke-RestMethod -Uri $webhook -Method Post -Body $body -ContentType "application/json; charset=utf-8" -TimeoutSec 30
            Write-Host "Webhook alert sent: variant_b_smoke_alert"
        }
        catch {
            Write-Warning "Webhook alert failed: $($_.Exception.Message)"
        }
    }
    else {
        Write-Host "Webhook alert skipped: no VARIANT_B_SMOKE_WEBHOOK_URL or OPS_ALARM_WEBHOOK_URL" -ForegroundColor DarkGray
    }
}

exit $exitCode
