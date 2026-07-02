# P0-2 G12 staging — probe keys + redirect URL validation (no payapp.kr open, no charge).

param(

    [string]$BaseUrl = "http://localhost:3010",

    [switch]$RequireG12,

    [switch]$SkipLiveDev

)



$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent

$reportPath = Join-Path $root "reports/logos_inquiry_p02_g12_staging_wire_v1_latest.json"

$startedUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$steps = @()

$g12Ready = $false



function Step-Ok([string]$Name) {

    $script:steps += @{ step = $Name; ok = $true }

}



Set-Location $root



$dotenvScript = Join-Path $root "scripts/Import-WorkspaceDotEnv_v1.ps1"

if (Test-Path -LiteralPath $dotenvScript) {

    . $dotenvScript -WorkspaceRoot $root

}



Write-Host "[g12-staging] probe PAYAPP_KEY presence (fingerprint only)"

$probeArgs = @("scripts/probe_logos_inquiry_payapp_g12_v1.py")

if ($RequireG12) { $probeArgs += "--require-g12" }

py @probeArgs

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Step-Ok "g12_probe"



$probeJson = Get-Content (Join-Path $root "reports/logos_inquiry_payapp_g12_probe_v1_latest.json") -Raw | ConvertFrom-Json

$g12Ready = [bool]$probeJson.g12_ready



if (-not $SkipLiveDev) {

    Write-Host "[g12-staging] dev preflight base=$BaseUrl"

    Push-Location (Join-Path $root "projects/no1kmedi")

    node ./scripts/check-logos-inquiry-dev-chunks-v1.mjs --base $BaseUrl

    if ($LASTEXITCODE -ne 0) {

        Write-Host "[g12-staging] start dev: npm run dev:logos (single instance)"

        Pop-Location

        exit $LASTEXITCODE

    }

    Step-Ok "dev_hydration_preflight"



    Write-Host "[g12-staging] G12 redirect smoke (env keys -> create; no browser)"

    npm run smoke:logos-inquiry-payapp-g12-redirect -- --base $BaseUrl

    if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }

    Step-Ok "g12_redirect_smoke"

    Pop-Location

} else {

    Write-Host "[g12-staging] skip live dev (-SkipLiveDev)"

}



$redirectPath = Join-Path $root "reports/logos_inquiry_payapp_g12_redirect_smoke_v1_latest.json"

$redirectSkipped = $false

if (Test-Path -LiteralPath $redirectPath) {

    $redirectJson = Get-Content $redirectPath -Raw | ConvertFrom-Json

    $redirectSkipped = [bool]$redirectJson.skipped

}



$mode = if ($g12Ready -and -not $redirectSkipped) { "g12_redirect_validated" }

        elseif ($redirectSkipped) { "g12_pending_human_inject" }

        else { "probe_only" }



$payload = @{

    schema           = "logos_inquiry_p02_g12_staging_wire_v1"

    ok               = $true

    mode             = $mode

    phase            = "P0-2"

    send_gate        = "HOLD"

    g12_ready        = $g12Ready

    redirect_skipped = $redirectSkipped

    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    started_at_utc   = $startedUtc

    steps            = $steps

    reproduce        = "powershell -File scripts/Invoke-LogosInquiryP02G12Staging_v1.ps1"

    require_g12      = "powershell -File scripts/Invoke-LogosInquiryP02G12Staging_v1.ps1 -RequireG12"

} | ConvertTo-Json -Depth 6

Set-Content -Path $reportPath -Value $payload -Encoding UTF8



Write-Host "[g12-staging] OK mode=$mode g12_ready=$g12Ready -> $reportPath"

