# P0-2 logos inquiry PayApp E2E wire — offline default (no dev server, no live charge).

param(

    [switch]$IncludeP01bWire,

    [switch]$IncludeLiveCheckout,

    [string]$BaseUrl = "http://localhost:3010"

)



$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent

$reportPath = Join-Path $root "reports/logos_inquiry_p02_payapp_wire_v1_latest.json"

$startedUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$steps = @()



function Step-Ok([string]$Name) {

    $script:steps += @{ step = $Name; ok = $true }

}



Set-Location $root



Write-Host "[p02-wire] PayApp scaffold smoke (pytest + contract)"

py scripts/run_logos_inquiry_payapp_e2e_smoke_v1.py

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Step-Ok "payapp_scaffold_smoke"



Write-Host "[p02-wire] offline HTTP chain (route handlers, no dev)"

Push-Location (Join-Path $root "projects/no1kmedi")

npm run smoke:logos-inquiry-payapp-http

if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }

Step-Ok "offline_payapp_http_chain"



if ($IncludeLiveCheckout) {

    Write-Host "[p02-wire] LIVE dev required base=$BaseUrl"

    node ./scripts/check-logos-inquiry-dev-chunks-v1.mjs --base $BaseUrl

    if ($LASTEXITCODE -ne 0) {

        Write-Host "[p02-wire] dev chunks fail — npm run stop:logos-dev && rm .next && npm run dev:logos"

        Pop-Location

        exit $LASTEXITCODE

    }

    Step-Ok "dev_hydration_preflight"



    npm run smoke:logos-inquiry-payapp-http:live -- --base $BaseUrl

    if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }

    Step-Ok "live_payapp_http_chain"

}



Pop-Location



if ($IncludeP01bWire) {

    Write-Host "[p02-wire] bundle P0-1b offline wire"

    & (Join-Path $root "scripts/Invoke-LogosInquiryP01bWire_v1.ps1")

    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Step-Ok "p01b_offline_wire"

}



$mode = if ($IncludeLiveCheckout) { "offline+live" } else { "offline_only" }

$payload = @{

    schema           = "logos_inquiry_p02_payapp_wire_v1"

    ok               = $true

    mode             = $mode

    phase            = "P0-2"

    send_gate        = "HOLD"

    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    started_at_utc   = $startedUtc

    steps            = $steps

    reproduce        = "powershell -File scripts/Invoke-LogosInquiryP02PayAppWire_v1.ps1"

    live_reproduce   = "powershell -File scripts/Invoke-LogosInquiryP02PayAppWire_v1.ps1 -IncludeLiveCheckout -BaseUrl http://localhost:3010"

    bundle_reproduce = "powershell -File scripts/Invoke-LogosInquiryP02PayAppWire_v1.ps1 -IncludeP01bWire"

} | ConvertTo-Json -Depth 6

Set-Content -Path $reportPath -Value $payload -Encoding UTF8



Write-Host "[p02-wire] OK $mode -> $reportPath"

