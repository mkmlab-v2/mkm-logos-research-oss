# Premium CS closure: deck + compression bridge + customer-provided intake + cross-lane ROI proxy (SEND HOLD).

param(

    [string]$WorkspaceRoot = "C:\workspace",

    [string]$WttTenantId = "wtt-customer-live-v1",

    [string]$CompressionTenantId = "wtt-premium-cs-compression-v1",

    [string]$WttJsonl = "data/wtt/intake/wtt-customer-live-v1.jsonl",

    [string]$CustomerProvidedJsonl = "data/wtt/intake/wtt-premium-cs-customer-live-v1.jsonl",

    [string]$CustomerProvidedCompressionTenantId = "wtt-premium-cs-customer-v1",

    [switch]$SkipCompressionIntake,

    [switch]$SkipCustomerProvidedIntake,

    [switch]$SkipBtrackCsShortContext,

    [switch]$DryRun

)



$ErrorActionPreference = "Stop"

$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path

Set-Location -LiteralPath $WorkspaceRoot



Write-Host "=== WTT Premium CS Closure ===" -ForegroundColor Cyan

Write-Host "deck + compression bridge + customer-provided | research_only | SEND HOLD" -ForegroundColor Yellow



if ($DryRun) {

    Write-Host "[DryRun] deck refresh -> export bridge -> compression intake(s) -> cross-lane status" -ForegroundColor DarkGray

    exit 0

}



Write-Host "=== 1/5: operator panel deck refresh (spicy SSOT) ===" -ForegroundColor Cyan

& powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-WttOperatorPanelDeckRefresh_v1.ps1

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



Write-Host "=== 2/5: WTT -> compression bridge export ===" -ForegroundColor Cyan

& py scripts/export_wtt_sessions_to_compression_corpus_v1.py --jsonl $WttJsonl --tenant-id $WttTenantId

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



if (-not $SkipCompressionIntake) {

    Write-Host "=== 3/5: compression bridge pilot intake (n30 RelaxPassGate PoC) ===" -ForegroundColor Cyan

    $bridge = Join-Path $WorkspaceRoot "data/compression/examples/wtt_premium_cs_compression_bridge_v1.jsonl"

    $bridgeArgs = @(
        "-TenantId", $CompressionTenantId,
        "-CustomerJsonl", $bridge,
        "-MaxCases", "30",
        "-MinCases", "20",
        "-RelaxPassGate"
    )
    if (-not $SkipBtrackCsShortContext) {
        $bridgeArgs += "-BtrackCsShortContext"
        Write-Host "btrack: bridge lane -BtrackCsShortContext [HYPO]" -ForegroundColor DarkYellow
    }

    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-CompressionCustomerPilotIntake_v1.ps1 @bridgeArgs

    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

} else {

    Write-Host "=== 3/5: bridge compression intake skipped ===" -ForegroundColor DarkGray

}



if (-not $SkipCustomerProvidedIntake) {

    $custPath = if ([System.IO.Path]::IsPathRooted($CustomerProvidedJsonl)) {

        $CustomerProvidedJsonl

    } else {

        Join-Path $WorkspaceRoot $CustomerProvidedJsonl

    }

    if (Test-Path -LiteralPath $custPath) {

        $custRows = (Get-Content -LiteralPath $custPath | Where-Object { $_.Trim() -ne "" }).Count
        $custMax = [Math]::Min(50, $custRows)
        Write-Host "=== 4/5: customer-provided compression intake ($custRows-row live) ===" -ForegroundColor Cyan

        $custArgs = @(

            "-TenantId", $CustomerProvidedCompressionTenantId,

            "-CustomerJsonl", $CustomerProvidedJsonl,

            "-MaxCases", "$custMax",

            "-MinCases", "$custMax",

            "-RelaxPassGate"

        )

        if (-not $SkipBtrackCsShortContext) {

            $custArgs += "-BtrackCsShortContext"

            Write-Host "btrack: -BtrackCsShortContext (economy shortcap 30/0.35 + strip prefixes) [HYPO]" -ForegroundColor DarkYellow

        }

        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-CompressionCustomerPilotIntake_v1.ps1 @custArgs

        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    } else {

        Write-Host "=== 4/5: customer-provided JSONL missing — skip ($CustomerProvidedJsonl) ===" -ForegroundColor Yellow

    }

} else {

    Write-Host "=== 4/5: customer-provided compression intake skipped ===" -ForegroundColor DarkGray

}



Write-Host "=== 5/5: rebuild stress deck + cross-lane status ===" -ForegroundColor Cyan

& py scripts/build_wtt_stress_certified_deck_v1.py

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



& py scripts/check_wtt_customer_intake_readiness_v1.py

& py scripts/build_wtt_premium_cs_cross_lane_status_v1.py

Write-Host "OK cross-lane: reports/wtt_premium_cs_cross_lane_status_v1_latest.json" -ForegroundColor Green

Write-Host "OK deck: reports/wtt_stress_certified_deck_v1_latest.md" -ForegroundColor Green

Write-Host "OK bridge: data/compression/examples/wtt_premium_cs_compression_bridge_v1.jsonl" -ForegroundColor Green

exit 0

