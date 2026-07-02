# Logos inquiry open beta wire — OSS verify + P0-1b offline + surface (payment deferred).

param(

    [switch]$IncludeP01bWire

)



$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent

$reportPath = Join-Path $root "reports/logos_inquiry_beta_wire_v1_latest.json"

$startedUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$steps = @()



function Step-Ok([string]$Name) {

    $script:steps += @{ step = $Name; ok = $true }

}



Set-Location $root



Write-Host "[beta-wire] public beta pack (surface + OSS + pytest)"

py scripts/run_logos_inquiry_beta_pack_v1.py

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Step-Ok "beta_pack"



if ($IncludeP01bWire) {

    Write-Host "[beta-wire] P0-1b hybrid stream offline"

    & (Join-Path $root "scripts/Invoke-LogosInquiryP01bWire_v1.ps1")

    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Step-Ok "p01b_offline"

}



$payload = @{

    schema           = "logos_inquiry_beta_wire_v1"

    ok               = $true

    mode             = "open_beta_polish"

    payment          = "deferred_post_oss"

    send_gate        = "HOLD"

    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    started_at_utc   = $startedUtc

    steps            = $steps

    reproduce        = "powershell -File scripts/Invoke-LogosInquiryBetaWire_v1.ps1"

    bundle_reproduce = "powershell -File scripts/Invoke-LogosInquiryBetaWire_v1.ps1 -IncludeP01bWire"

} | ConvertTo-Json -Depth 6

Set-Content -Path $reportPath -Value $payload -Encoding UTF8



Write-Host "[beta-wire] OK -> $reportPath"

