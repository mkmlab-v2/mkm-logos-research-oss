#Requires -Version 5.1
<#
.SYNOPSIS
  PersonaDiary Android Intent E2E — deep link + share via adb (research_only · [HYPO]).

.EXAMPLE
  powershell -File scripts\Invoke-PersonadiaryAndroidIntentE2e_v1.ps1 -SkipEmulatorStart

.EXAMPLE
  powershell -File scripts\Invoke-PersonadiaryAndroidIntentE2e_v1.ps1
#>
param(
    [string]$AvdName = "Medium_Phone_API_36.1",
    [switch]$SkipEmulatorStart,
    [switch]$SkipInstall,
    [int]$WebViewWarmupSeconds = 18,
    [int]$IntentSettleSeconds = 6
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pkg = "com.mkmlife.personadiary.hypo"
$outJson = Join-Path $root "reports\personadiary_android_intent_e2e_latest.json"
$shotPng = Join-Path $root "reports\personadiary_android_intent_e2e_latest.png"

$env:ANDROID_HOME = Join-Path $env:LOCALAPPDATA "Android\Sdk"
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:PATH = "$env:JAVA_HOME\bin;$env:ANDROID_HOME\platform-tools;$env:ANDROID_HOME\emulator;$env:PATH"
$adb = Join-Path $env:ANDROID_HOME "platform-tools\adb.exe"

if (-not (Test-Path $adb)) { Write-Error "adb not found: $adb" }

$emuArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\Invoke-PersonadiaryAndroidEmulatorRun_v1.ps1")
if ($SkipEmulatorStart) { $emuArgs += "-SkipEmulatorStart" }
if ($SkipInstall) { $emuArgs += "-SkipInstall" }
& powershell.exe @emuArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Start-Sleep -Seconds $WebViewWarmupSeconds
& $adb logcat -c | Out-Null

$momentToken = "pd_e2e_moment_v1"
$reminderToken = "pd_e2e_reminder_v1"
$shareToken = "pd_e2e_share_v1"

$probes = @()

function Invoke-IntentProbe {
    param(
        [string]$Id,
        [scriptblock]$Fire,
        [string]$ExpectUi
    )
    & $adb logcat -c | Out-Null
    & $Fire
    Start-Sleep -Seconds $IntentSettleSeconds
    $pidOut = (& $adb shell pidof $pkg 2>$null | Select-Object -First 1) -replace "[\r\n]", ""
    & $adb shell uiautomator dump /sdcard/window_dump.xml 2>$null | Out-Null
    $uiXml = (& $adb shell cat /sdcard/window_dump.xml 2>$null | Out-String)
    $logTail = (& $adb logcat -d -t 400 2>$null | Out-String)
    $uiHit = $uiXml -match [regex]::Escape($ExpectUi)
    $logHit = $logTail -match [regex]::Escape("[pd-intent-e2e-v1]")
    $ok = [bool]$pidOut -and ($uiHit -or $logHit)
    return @{
        id = $Id
        ok = $ok
        pid = $pidOut
        expect_ui = $ExpectUi
        ui_hit = $uiHit
        log_hit = $logHit
    }
}

function Invoke-AmStartViewUri {
    param([string]$Uri)
    # Quote URI for device shell — unescaped & breaks add_reminder due_local param.
    $safe = $Uri -replace "'", "'\\''"
    & $adb shell "am start -a android.intent.action.VIEW -d '$safe' -n $pkg/.MainActivity" | Out-Null
}

$probes += Invoke-IntentProbe -Id "save_moment_note" -ExpectUi $momentToken -Fire {
    $uri = "personadiary://intent/save_moment_note?text=$momentToken&lane=mind"
    Invoke-AmStartViewUri -Uri $uri
}

$probes += Invoke-IntentProbe -Id "add_reminder" -ExpectUi $reminderToken -Fire {
    $uri = "personadiary://intent/add_reminder?text=$reminderToken&lane=rest&due_local=2026-06-22"
    Invoke-AmStartViewUri -Uri $uri
}

$probes += Invoke-IntentProbe -Id "share_text" -ExpectUi $shareToken -Fire {
    & $adb shell "am start -a android.intent.action.SEND -t text/plain --es android.intent.extra.TEXT $shareToken -n $pkg/.MainActivity" | Out-Null
}

cmd /c "`"$adb`" exec-out screencap -p > `"$shotPng`"" | Out-Null
$shotOk = (Test-Path $shotPng) -and ((Get-Item $shotPng).Length -gt 1000)
$overallOk = ($probes | Where-Object { $_.ok -eq $false }).Count -eq 0 -and $shotOk

$report = @{
    schema = "personadiary_android_intent_e2e_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    research_only = $true
    hypothesis_tier = "B"
    package = $pkg
    avd = $AvdName
    probes = $probes
    screenshot_path = if ($shotOk) { "reports/personadiary_android_intent_e2e_latest.png" } else { $null }
    ok = $overallOk
}
$jsonText = $report | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($outJson, $jsonText, [System.Text.UTF8Encoding]::new($false))
Write-Host "WROTE: $outJson"
$probes | ForEach-Object { Write-Host "$($_.id) ok=$($_.ok) ui_hit=$($_.ui_hit) log_hit=$($_.log_hit)" }
exit $(if ($overallOk) { 0 } else { 1 })
