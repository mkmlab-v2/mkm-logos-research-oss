#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Remove known safe junk from C:\ root (VS2010 External Installer extract + demo gif).
  Does NOT touch pagefile/hiberfil/Python311/workspace/repos/AMD/Windows.
#>
$ErrorActionPreference = 'Continue'
$targets = @(
  'C:\team-dna-demo.gif',
  'C:\eula.1028.txt','C:\eula.1031.txt','C:\eula.1033.txt','C:\eula.1036.txt','C:\eula.1040.txt',
  'C:\eula.1041.txt','C:\eula.1042.txt','C:\eula.1049.txt','C:\eula.2052.txt','C:\eula.3082.txt',
  'C:\globdata.ini','C:\install.exe','C:\install.ini',
  'C:\install.res.1028.dll','C:\install.res.1031.dll','C:\install.res.1033.dll','C:\install.res.1036.dll',
  'C:\install.res.1040.dll','C:\install.res.1041.dll','C:\install.res.1042.dll','C:\install.res.1049.dll',
  'C:\install.res.2052.dll','C:\install.res.3082.dll'
)
foreach ($f in $targets) {
  if (-not (Test-Path -LiteralPath $f)) { continue }
  try {
    & takeown.exe /F $f /A | Out-Null
    & icacls.exe $f /grant:r "*S-1-5-32-544:F" | Out-Null
  } catch {}
  try {
    Remove-Item -LiteralPath $f -Force -ErrorAction Stop
    Write-Host "Removed $f"
  } catch {
    Write-Warning "Failed $f : $($_.Exception.Message)"
  }
}
Write-Host "Done. Exit 0"
exit 0
