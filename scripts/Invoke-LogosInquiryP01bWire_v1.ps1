# P0-1b logos inquiry hybrid stream wire — offline default (no dev server).
# Live SSE + Playwright: -IncludeLiveAsk -BaseUrl http://localhost:3010
param(
    [switch]$IncludeLiveAsk,
    [string]$BaseUrl = "http://localhost:3010"
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$reportPath = Join-Path $root "reports/logos_inquiry_p01b_wire_v1_latest.json"
$startedUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$steps = @()

function Step-Ok([string]$Name) {
    $script:steps += @{ step = $Name; ok = $true }
}

Set-Location $root

Write-Host "[p01b-wire] pytest logos_inquiry stream+report (offline)"
py -m pytest tests/test_logos_inquiry_stream_v1.py tests/test_logos_inquiry_report_v1.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Step-Ok "pytest_stream_report"

Write-Host "[p01b-wire] freeze stream contract (offline)"
py scripts/run_logos_inquiry_stream_schema_freeze_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Step-Ok "freeze_stream_contract"

Write-Host "[p01b-wire] offline TS hybrid sequence (no dev server)"
Push-Location (Join-Path $root "projects/no1kmedi")
npm run smoke:logos-inquiry-stream
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Step-Ok "offline_ts_stream_sequence"

if ($IncludeLiveAsk) {
    Write-Host "[p01b-wire] LIVE dev required base=$BaseUrl"
    node ./scripts/check-logos-inquiry-dev-chunks-v1.mjs --base $BaseUrl
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[p01b-wire] dev chunks fail — single dev only: npm run dev:logos"
        Pop-Location
        exit $LASTEXITCODE
    }
    Step-Ok "dev_hydration_preflight"

    node ./scripts/smoke-logos-inquiry-ask-ui-v1.mjs --base $BaseUrl
    if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
    Step-Ok "live_sse_ask"

    node ./scripts/smoke-logos-inquiry-ask-playwright-v1.mjs --base $BaseUrl
    if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
    Step-Ok "playwright_ask_hybrid"
} else {
    Write-Host "[p01b-wire] skip live ask (offline-only; use -IncludeLiveAsk for dev UI)"
}

Pop-Location

$payload = @{
    schema           = "logos_inquiry_p01b_wire_v1"
    ok               = $true
    mode             = if ($IncludeLiveAsk) { "offline+live" } else { "offline_only" }
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    started_at_utc   = $startedUtc
    steps            = $steps
    reproduce        = "powershell -File scripts/Invoke-LogosInquiryP01bWire_v1.ps1"
    live_reproduce   = "powershell -File scripts/Invoke-LogosInquiryP01bWire_v1.ps1 -IncludeLiveAsk -BaseUrl http://localhost:3010"
} | ConvertTo-Json -Depth 6
Set-Content -Path $reportPath -Value $payload -Encoding UTF8

Write-Host "[p01b-wire] OK offline$(if ($IncludeLiveAsk) { '+live' }) -> $reportPath"
