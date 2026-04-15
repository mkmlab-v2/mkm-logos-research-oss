Param(

    [string]$WorkspaceRoot = "C:\workspace",

    [string]$StatusJson = "docs/final/artifacts/kospi_biblical_single_lane_stability_status_latest.json"

)



Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"



if (-not (Test-Path -LiteralPath $WorkspaceRoot)) {

    throw "Workspace root not found: $WorkspaceRoot"

}



Push-Location $WorkspaceRoot

try {

    $path = Join-Path $WorkspaceRoot $StatusJson

    if (-not (Test-Path -LiteralPath $path)) {

        Write-Host "[live-readiness] missing status file: $path"

        exit 2

    }

    $j = Get-Content -LiteralPath $path -Raw -Encoding utf8 | ConvertFrom-Json

    $lt = $j.live_trading

    if ($null -eq $lt) {

        Write-Host "[live-readiness] live_trading block missing in status JSON"

        exit 3

    }

    $allowed = [bool]$lt.allowed

    if ($allowed) {

        Write-Host ("[live-readiness] OK phase={0} allowed=true" -f $lt.phase)

        exit 0

    }

    Write-Host ("[live-readiness] BLOCKED phase={0}" -f $lt.phase)

    foreach ($r in @($lt.reasons_if_blocked)) {

        Write-Host ("  - {0}" -f $r)

    }

    exit 1

}

finally {

    Pop-Location

}


