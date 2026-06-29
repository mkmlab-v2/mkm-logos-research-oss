# npm install + cap add android/ios (if missing) + cap sync for PersonaDiary hypo shell.

param(

    [ValidateSet("Android", "Ios", "Both")]

    [string]$Platform = "Both",

    [switch]$SkipAndroidAdd,

    [switch]$SkipIosAdd,

    [switch]$WhatIfOnly

)



$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path (Join-Path $root "projects\no1kmedi\personadiary-native-hypo-v1\package.json"))) {

    $root = Split-Path -Parent $PSScriptRoot

}



$shellDir = Join-Path $root "projects\no1kmedi\personadiary-native-hypo-v1"

$outJson = Join-Path $root "reports\personadiary_native_shell_hypo_bootstrap_latest.json"

$copyContract = Join-Path $root "docs\final\artifacts\personadiary_non_prediction_copy_contract_v1_latest.json"



if (-not (Test-Path $shellDir)) {

    Write-Error "missing shell dir: $shellDir"

}



$wantAndroid = $Platform -eq "Android" -or $Platform -eq "Both"

$wantIos = $Platform -eq "Ios" -or $Platform -eq "Both"



Push-Location $shellDir

try {

    $steps = @()



    if ($WhatIfOnly) {

        @{

            schema = "personadiary_native_shell_hypo_bootstrap_v1"

            what_if_only = $true

            platform = $Platform

            shell_dir = $shellDir

            copy_contract_present = (Test-Path $copyContract)

        } | ConvertTo-Json | Set-Content -Path $outJson -Encoding UTF8

        Write-Host "WhatIf: would run npm install + cap sync ($Platform) in $shellDir"

        exit 0

    }



    Write-Host "[1/4] npm install ..."

    npm install --no-fund --no-audit

    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $steps += @{ step = "npm_install"; exit_code = 0 }



    $androidDir = Join-Path $shellDir "android"

    if ($wantAndroid -and -not $SkipAndroidAdd -and -not (Test-Path $androidDir)) {

        Write-Host "[2/4] npx cap add android ..."

        npx cap add android

        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

        $steps += @{ step = "cap_add_android"; exit_code = 0 }

    }

    else {

        $steps += @{ step = "cap_add_android"; skipped = $true; wanted = $wantAndroid }

    }



    $iosDir = Join-Path $shellDir "ios"

    if ($wantIos -and -not $SkipIosAdd -and -not (Test-Path $iosDir)) {

        Write-Host "[3/4] npx cap add ios ..."

        npx cap add ios

        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

        $steps += @{ step = "cap_add_ios"; exit_code = 0 }

    }

    else {

        $steps += @{ step = "cap_add_ios"; skipped = $true; wanted = $wantIos }

    }



    Write-Host "[4/4] npx cap sync ..."

    npx cap sync

    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $steps += @{ step = "cap_sync"; exit_code = 0 }



    $report = @{

        schema = "personadiary_native_shell_hypo_bootstrap_v1"

        generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

        research_only = $true

        hypothesis_tier = "B"

        platform = $Platform

        shell_dir = "projects/no1kmedi/personadiary-native-hypo-v1"

        copy_contract = "docs/final/artifacts/personadiary_non_prediction_copy_contract_v1_latest.json"

        copy_contract_present = (Test-Path $copyContract)

        android_dir_present = (Test-Path $androidDir)

        ios_dir_present = (Test-Path $iosDir)

        node_modules_present = (Test-Path (Join-Path $shellDir "node_modules"))

        steps = $steps

        ok = $true

    }

    $report | ConvertTo-Json -Depth 6 | Set-Content -Path $outJson -Encoding UTF8

    Write-Host "WROTE: $outJson"

    exit 0

}

finally {

    Pop-Location

}

