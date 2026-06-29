#Requires -Version 5.1
<#
.SYNOPSIS
  Daily B2B Logos smoke: deploy verify + lemma live + demo preset batch.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-LogosStudioB2bDailySmoke_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$BaseUrl = "https://logos.jema-ai.com",
    [int]$TimeoutSeconds = 180,
    [switch]$SkipPresetBatch
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$steps = @(
    @{
        id = "deploy_verify"
        cmd  = @(
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", (Join-Path $WorkspaceRoot "scripts\verify_logos_jema_ai_deploy_v1.ps1"),
            "-BaseUrl", $BaseUrl
        )
    },
    @{
        id = "lemma_bridge_live"
        cmd  = @(
            "py", (Join-Path $WorkspaceRoot "scripts\check_logos_studio_lemma_bridge_live_smoke_v1.py"),
            "--base", $BaseUrl,
            "--timeout-s", "$TimeoutSeconds"
        )
    }
)

if (-not $SkipPresetBatch) {
    $steps += @{
        id = "demo_preset_batch"
        cmd  = @(
            "py", (Join-Path $WorkspaceRoot "scripts\check_logos_studio_b2b_demo_preset_batch_v1.py"),
            "--base", $BaseUrl,
            "--timeout-s", "$TimeoutSeconds"
        )
    }
}

$failures = @()
foreach ($step in $steps) {
    Write-Host "[logos-b2b-daily] $($step.id)" -ForegroundColor Cyan
    $cmd = @($step.cmd)
    & $cmd[0] @($cmd[1..($cmd.Length - 1)])
    if ($LASTEXITCODE -ne 0) {
        $failures += $step.id
    }
}

$out = Join-Path $WorkspaceRoot "reports\logos_studio_b2b_daily_smoke_v1_latest.json"
$doc = [ordered]@{
    schema             = "logos_studio_b2b_daily_smoke_v1"
    generated_at_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    base_url           = $BaseUrl
    ok                 = ($failures.Count -eq 0)
    gate_failures      = @($failures)
    steps              = @($steps | ForEach-Object { $_.id })
    reproduce          = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-LogosStudioB2bDailySmoke_v1.ps1"
}
$doc | ConvertTo-Json -Depth 6 | Set-Content -Path $out -Encoding UTF8

if ($failures.Count -gt 0) {
    Write-Host "[logos-b2b-daily] FAIL: $($failures -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "[logos-b2b-daily] OK report=$out" -ForegroundColor Green
exit 0
