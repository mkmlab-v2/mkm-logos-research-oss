#Requires -Version 5.1
<#
  Shared helpers for Cursor IDE Browser Automation (browser_* direct execution).
  SSOT: docs/final/artifacts/cursor_ide_browser_automation_recovery_v1.json
#>

function Get-CursorExePath {
    $cursorExe = Join-Path $env:LOCALAPPDATA "Programs\cursor\Cursor.exe"
    if (-not (Test-Path -LiteralPath $cursorExe)) {
        throw "Cursor.exe not found: $cursorExe"
    }
    return $cursorExe
}

function Invoke-CursorCli {
    param(
        [string[]]$CliArgs
    )
    $cursorExe = Get-CursorExePath
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $cursorExe @CliArgs 2>&1 | Out-Null
    $ErrorActionPreference = $prev
}

function Open-CursorIdeBrowserTab {
    param(
        [string]$WorkspaceRoot = "C:\workspace",
        [int]$SleepSeconds = 1
    )
    Invoke-CursorCli @("--reuse-window", $WorkspaceRoot)
    Start-Sleep -Seconds 2
    $browserCmds = @(
        "cursor.browserTabEnabled",
        "workbench.action.newBrowserTab",
        "cursor.browserView.newTab",
        "cursor.browserView.focusOrShowTab",
        "workbench.action.focusOrOpenBrowserEditor",
        "workbench.action.openBrowserEditor"
    )
    foreach ($cmd in $browserCmds) {
        Invoke-CursorCli @("--reuse-window", $WorkspaceRoot, "--command", $cmd)
        Start-Sleep -Seconds $SleepSeconds
    }
}

function Test-CursorProcessRunning {
    return [bool](Get-Process -Name "Cursor" -ErrorAction SilentlyContinue | Select-Object -First 1)
}
