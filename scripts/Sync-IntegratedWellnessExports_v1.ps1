# Publish IWS v2 chain outputs to no1kmedi public static paths (local dev).
param(
    [string]$SeedJson = "",
    [string]$ConsultJson = "",
    [switch]$Validate
)

$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { Get-Location }

$args = @(
    "scripts/publish_integrated_wellness_solution_v2_exports_v1.py",
    "--out-dir", "reports/integrated_wellness_solution_v2_chain",
    "--no1kmedi-public", "projects/no1kmedi/public/data/integrated_wellness",
    "--personadiary-public", "projects/no1kmedi/public/data",
    "--mkmlife-public", "projects/mkm/mkm-life/public/data"
)

if ($SeedJson) { $args += @("--seed-json", $SeedJson) }
elseif ($ConsultJson) { $args += @("--consult-json", $ConsultJson) }
else {
    $args += @(
        "--seed-json",
        "docs/final/artifacts/fixtures/integrated_wellness_solution_v2_minor_soeum_abdomen_seed.example.json"
    )
}
if ($Validate) { $args += "--validate" }

Push-Location $Root
try {
    py @args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $iwsDir = "projects/no1kmedi/public/data/integrated_wellness"
    New-Item -ItemType Directory -Force -Path $iwsDir | Out-Null
    Copy-Item -Force `
        "reports/integrated_wellness_solution_v2_chain/personadiary_daily_package_latest.json" `
        "projects/no1kmedi/public/data/personadiary_daily_response_package_v1.json"
    Copy-Item -Force `
        "reports/integrated_wellness_solution_v2_chain/personadiary_daily_package_latest.json" `
        "$iwsDir/personadiary_iws_overlay_v1.json"
    Copy-Item -Force `
        "reports/integrated_wellness_solution_v2_chain/personadiary_daily_package_latest.json" `
        "$iwsDir/personadiary_daily_package_latest.json"
    Write-Host "OK: IWS v2 exports synced to projects/no1kmedi/public/data (+ integrated_wellness overlay)"
}
finally {
    Pop-Location
}
