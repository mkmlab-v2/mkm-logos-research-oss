# CLI: start AVD, installDebug, launch PersonaDiary hypo shell (research_only).
param(
    [string]$AvdName = "Medium_Phone_API_36.1",
    [switch]$SkipEmulatorStart,
    [switch]$SkipInstall,
    [switch]$ColdBoot,
    [switch]$KillRunningEmulator,
    [int]$BootWaitSeconds = 240,
    [int]$PostBootStabilizeSeconds = 12,
    [int]$AppLoadWaitSeconds = 32
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$shellDir = Join-Path $root "projects\no1kmedi\personadiary-native-hypo-v1"
$androidDir = Join-Path $shellDir "android"
$outJson = Join-Path $root "reports\personadiary_android_emulator_run_latest.json"
$shotPng = Join-Path $root "reports\personadiary_android_emulator_smoke_latest.png"
$pkg = "com.mkmlife.personadiary.hypo"

$env:ANDROID_HOME = Join-Path $env:LOCALAPPDATA "Android\Sdk"
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:PATH = "$env:JAVA_HOME\bin;$env:ANDROID_HOME\platform-tools;$env:ANDROID_HOME\emulator;$env:PATH"

$adb = Join-Path $env:ANDROID_HOME "platform-tools\adb.exe"
$emu = Join-Path $env:ANDROID_HOME "emulator\emulator.exe"

if (-not (Test-Path $adb)) { Write-Error "adb not found: $adb" }
if (-not (Test-Path $androidDir)) { Write-Error "android dir missing: $androidDir" }

$steps = @()

function Invoke-EmulatorPerfTuning {
    & $adb shell settings put global window_animation_scale 0 2>$null | Out-Null
    & $adb shell settings put global transition_animation_scale 0 2>$null | Out-Null
    & $adb shell settings put global animator_duration_scale 0 2>$null | Out-Null
}

function Invoke-DismissSystemAnrIfPresent {
    $dump = (& $adb shell dumpsys window windows 2>$null | Out-String)
    if ($dump -match "isn't responding" -or $dump -match "Application Not Responding") {
        # Select "Wait" (DPAD_RIGHT + ENTER) — best-effort on API 36 system dialog
        & $adb shell input keyevent 22 2>$null | Out-Null
        Start-Sleep -Milliseconds 400
        & $adb shell input keyevent 66 2>$null | Out-Null
        return $true
    }
    return $false
}

if ($KillRunningEmulator) {
    try {
        & $adb emu kill 2>$null | Out-Null
    }
    catch {
        # no emulator — safe to continue
    }
    Start-Sleep -Seconds 3
    $steps += @{ step = "emulator_kill"; ok = $true }
}

if (-not $SkipEmulatorStart) {
    $devices = & $adb devices
    if ($devices -notmatch "emulator-\d+\s+device") {
        if (-not (Test-Path $emu)) { Write-Error "emulator not found: $emu" }
        $emuArgs = @(
            "-avd", $AvdName,
            "-no-boot-anim",
            "-no-audio",
            "-gpu", "swiftshader_indirect",
            "-memory", "4096",
            "-cores", "4"
        )
        if ($ColdBoot) {
            $emuArgs += @("-no-snapshot-load", "-no-snapshot-save")
        }
        Start-Process -FilePath $emu -ArgumentList $emuArgs -WindowStyle Minimized
        $steps += @{ step = "emulator_start"; avd = $AvdName; cold_boot = [bool]$ColdBoot }
        & $adb wait-for-device | Out-Null
        $deadline = (Get-Date).AddSeconds($BootWaitSeconds)
        do {
            Start-Sleep -Seconds 5
            $raw = & $adb shell getprop sys.boot_completed 2>$null
            $boot = ($raw | Select-Object -First 1) -replace "[\r\n]", ""
        } while ($boot -ne "1" -and (Get-Date) -lt $deadline)
        if ($boot -ne "1") { Write-Error "emulator boot timeout" }
        if ($PostBootStabilizeSeconds -gt 0) {
            Start-Sleep -Seconds $PostBootStabilizeSeconds
            $steps += @{ step = "post_boot_stabilize"; seconds = $PostBootStabilizeSeconds }
        }
        Invoke-EmulatorPerfTuning
        $steps += @{ step = "emulator_perf_tuning"; animations = "disabled" }
    }
    else {
        $steps += @{ step = "emulator_start"; skipped = "already_running" }
        Invoke-EmulatorPerfTuning
    }
}

if (-not $SkipInstall) {
    Push-Location $androidDir
    try {
        .\gradlew.bat installDebug --no-daemon
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        $steps += @{ step = "gradlew_installDebug"; exit_code = 0 }
    }
    finally {
        Pop-Location
    }
}

& $adb shell am force-stop $pkg | Out-Null
Start-Sleep -Seconds 2
& $adb shell am start -n "$pkg/.MainActivity" | Out-Null
Start-Sleep -Seconds $AppLoadWaitSeconds

$dismissedAnr = Invoke-DismissSystemAnrIfPresent
if ($dismissedAnr) {
    $steps += @{ step = "system_anr_dismiss_wait"; ok = $true }
    Start-Sleep -Seconds 8
}

$pidOut = (& $adb shell pidof $pkg 2>$null | Select-Object -First 1) -replace "[\r\n]", ""
$steps += @{ step = "am_start"; pid = $pidOut; app_load_wait_seconds = $AppLoadWaitSeconds }

cmd /c "`"$adb`" exec-out screencap -p > `"$shotPng`"" | Out-Null
$shotOk = (Test-Path $shotPng) -and ((Get-Item $shotPng).Length -gt 1000)

$uiXml = ""
try {
    & $adb shell uiautomator dump /sdcard/window_dump.xml 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $uiXml = (& $adb shell cat /sdcard/window_dump.xml 2>$null | Out-String)
    }
}
catch {
    $steps += @{ step = "uiautomator_dump"; warning = $_.Exception.Message }
}

$systemAnrVisible = $uiXml -match "isn't responding" -or $uiXml -match "Application Not Responding"
$webviewOk = ($uiXml -match 'package="com\.mkmlife\.personadiary\.hypo"') -and ($uiXml -match "android\.webkit\.WebView")
if (-not $webviewOk -and $pidOut) {
    $winDump = (& $adb shell dumpsys window windows 2>$null | Out-String)
    $actDump = (& $adb shell dumpsys activity activities 2>$null | Out-String)
    $webviewOk = (
        ($winDump -match "com\.mkmlife\.personadiary\.hypo") -or
        ($actDump -match "com\.mkmlife\.personadiary\.hypo/.MainActivity")
    )
    if ($webviewOk) {
        $steps += @{ step = "webview_probe"; method = "dumpsys_fallback" }
    }
    if (-not $systemAnrVisible) {
        $systemAnrVisible = $winDump -match "isn't responding"
    }
}
$fgRaw = (& $adb shell dumpsys activity activities 2>$null | Select-String -Pattern "mResumedActivity" | Select-Object -First 1)
$foregroundHint = if ($fgRaw) { ($fgRaw.Line -replace "\s+", " ").Trim() } else { $null }

$report = @{
    schema = "personadiary_android_emulator_run_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    research_only = $true
    hypothesis_tier = "B"
    package = $pkg
    avd = $AvdName
    screenshot_path = if ($shotOk) { "reports/personadiary_android_emulator_smoke_latest.png" } else { $null }
    screenshot_bytes = if ($shotOk) { (Get-Item $shotPng).Length } else { 0 }
    pid = $pidOut
    webview_ok = $webviewOk
    system_anr_visible = [bool]$systemAnrVisible
    foreground_activity_hint = $foregroundHint
    steps = $steps
    ok = [bool]$pidOut -and $webviewOk -and $shotOk -and (-not $systemAnrVisible)
}
$jsonText = $report | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($outJson, $jsonText, [System.Text.UTF8Encoding]::new($false))
Write-Host "WROTE: $outJson"
if (-not $pidOut) { exit 1 }
if ($systemAnrVisible) { exit 2 }
exit 0
