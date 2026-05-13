#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Remove C:\AMD driver installer extract cache (typically safe after drivers are installed).
#>
$path = 'C:\AMD'
if (-not (Test-Path -LiteralPath $path)) { Write-Host 'C:\AMD not present'; exit 0 }
try {
  & takeown.exe /F $path /R /D Y 2>&1 | Out-Null
  & icacls.exe $path /grant:r "*S-1-5-32-544:(OI)(CI)F" /T 2>&1 | Out-Null
} catch {}
Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction Stop
Write-Host "Removed $path"
exit 0
