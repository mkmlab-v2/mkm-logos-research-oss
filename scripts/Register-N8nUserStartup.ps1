[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$StartupLabel = "MKM-n8n-start",

    [switch]$Remove,
    [int]$StartupDelaySec = 45,
    [int]$HealthTimeoutSec = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$startupDir = [Environment]::GetFolderPath("Startup")
if ([string]::IsNullOrWhiteSpace($startupDir)) {
    throw "Could not resolve user Startup folder path."
}

$vbsPath = Join-Path $startupDir "$StartupLabel.vbs"

if ($Remove) {
    if (Test-Path -LiteralPath $vbsPath) {
        Remove-Item -LiteralPath $vbsPath -Force
        Write-Output "user_startup: REMOVED ($vbsPath)"
    }
    else {
        Write-Output "user_startup: NOTHING_TO_REMOVE ($vbsPath)"
    }
    exit 0
}

$guardScript = Join-Path $PSScriptRoot "Run-N8nServiceGuardV1.ps1"
if (-not (Test-Path -LiteralPath $guardScript)) {
    throw "Required script not found: $guardScript"
}

# VBScript: hidden window (0), do not wait. Guard script prevents duplicate starts.
$guardForVbs = $guardScript.Replace('"', '""')
$vbs = @"
Option Explicit
Dim sh, p
Set sh = CreateObject("WScript.Shell")
p = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File " & Chr(34) & "$guardForVbs" & Chr(34) & " -StartupDelaySec $StartupDelaySec -HealthTimeoutSec $HealthTimeoutSec"
sh.Run "cmd /c " & p, 0, False
"@

Set-Content -LiteralPath $vbsPath -Value $vbs -Encoding ASCII -Force
Write-Output "user_startup: REGISTERED ($vbsPath)"
Write-Output "guard_script=$guardScript"
