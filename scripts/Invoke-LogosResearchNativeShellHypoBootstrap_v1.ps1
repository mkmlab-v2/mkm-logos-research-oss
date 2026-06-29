# npm install + cap add android/ios (if missing) + cap sync for Logos Research hypo shell.

param(
    [ValidateSet("Android", "Ios", "Both")]
    [string]$Platform = "Android",
    [switch]$SkipAndroidAdd,
    [switch]$SkipIosAdd,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$shellDir = Join-Path $root "projects\no1kmedi\logos-research-native-hypo-v1"
$outJson = Join-Path $root "reports\logos_research_native_shell_hypo_bootstrap_latest.json"

if (-not (Test-Path $shellDir)) {
    Write-Error "missing shell dir: $shellDir"
}

$wantAndroid = $Platform -eq "Android" -or $Platform -eq "Both"
$wantIos = $Platform -eq "Ios" -or $Platform -eq "Both"

Push-Location $shellDir
try {
    if ($WhatIfOnly) {
        @{
            schema = "logos_research_native_shell_hypo_bootstrap_v1"
            what_if_only = $true
            platform = $Platform
            shell_dir = $shellDir
        } | ConvertTo-Json | Set-Content -Path $outJson -Encoding UTF8
        Write-Host "WhatIf: would run npm install + cap sync ($Platform) in $shellDir"
        exit 0
    }

    $steps = @()
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
    } else {
        $steps += @{ step = "cap_add_android"; skipped = $true; wanted = $wantAndroid }
    }

    $iosDir = Join-Path $shellDir "ios"
    if ($wantIos -and -not $SkipIosAdd -and -not (Test-Path $iosDir)) {
        Write-Host "[3/4] npx cap add ios ..."
        npx cap add ios
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        $steps += @{ step = "cap_add_ios"; exit_code = 0 }
    } else {
        $steps += @{ step = "cap_add_ios"; skipped = $true; wanted = $wantIos }
    }

    Write-Host "[4/4] npx cap sync ..."
    npx cap sync
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $steps += @{ step = "cap_sync"; exit_code = 0 }

    @{
        schema = "logos_research_native_shell_hypo_bootstrap_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        research_only = $true
        hypothesis_tier = "B"
        platform = $Platform
        shell_dir = "projects/no1kmedi/logos-research-native-hypo-v1"
        android_dir_present = (Test-Path $androidDir)
        ios_dir_present = (Test-Path $iosDir)
        node_modules_present = (Test-Path (Join-Path $shellDir "node_modules"))
        steps = $steps
        ok = $true
    } | ConvertTo-Json -Depth 6 | Set-Content -Path $outJson -Encoding UTF8
    Write-Host "WROTE: $outJson"
    exit 0
} finally {
    Pop-Location
}
