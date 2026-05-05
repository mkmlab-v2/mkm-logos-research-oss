[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$StartupLabel = "MKM-n8n-start",

    [switch]$Remove
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

$n8nCmd = (Get-Command -Name "n8n.cmd" -ErrorAction Stop).Source
if (-not (Test-Path -LiteralPath $n8nCmd)) {
    throw "n8n.cmd not found on PATH."
}

# VBScript: hidden window (0), do not wait for n8n (False). Quote path with Chr(34).
$n8nForVbs = $n8nCmd.Replace('"', '""')
$vbs = @"
Option Explicit
Dim sh, p
Set sh = CreateObject("WScript.Shell")
p = Chr(34) & "$n8nForVbs" & Chr(34)
sh.Run "cmd /c " & p & " start", 0, False
"@

Set-Content -LiteralPath $vbsPath -Value $vbs -Encoding ASCII -Force
Write-Output "user_startup: REGISTERED ($vbsPath)"
Write-Output "n8n_cmd=$n8nCmd"
