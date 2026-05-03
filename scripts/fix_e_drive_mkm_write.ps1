#Requires -Version 5.1
<#
.SYNOPSIS
  E: is often locked to RX for normal users. Creates E:\MKM_ARCHIVE_FROM_F and grants the
  interactive user Modify (inheritance) so tools can write without whole-drive ACL surgery.

.EXAMPLE
  # Right-click PowerShell -> Run as administrator, then:
  .\scripts\fix_e_drive_mkm_write.ps1

  # Or from repo root (will try to self-elevate):
  .\scripts\fix_e_drive_mkm_write.ps1 -SelfElevate
#>
param(
  [switch]$SelfElevate
)

$ErrorActionPreference = 'Stop'

function Test-IsAdmin {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  $p = New-Object Security.Principal.WindowsPrincipal($id)
  return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-LoggedOnUserForAcl {
  $cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
  if ($cs -and $cs.UserName) {
    return $cs.UserName.Trim()
  }
  return "$env:USERDOMAIN\$env:USERNAME"
}

if (-not (Test-IsAdmin)) {
  if ($SelfElevate) {
    $path = $MyInvocation.MyCommand.Path
    Write-Host "[INFO] Requesting elevation..." -ForegroundColor Yellow
    Start-Process -FilePath "pwsh.exe" -Verb RunAs -ArgumentList @(
      '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $path
    ) | Out-Null
    exit 0
  }
  Write-Error "Run this script as Administrator (elevated PowerShell), or use: -SelfElevate"
  exit 1
}

$grantee = Get-LoggedOnUserForAcl
$folders = @(
  'E:\MKM_ARCHIVE_FROM_F',
  'E:\02_Projects\MKM_ARCHIVE_FROM_F'
)

Write-Host "=== fix_e_drive_mkm_write (elevated) ===" -ForegroundColor Cyan
Write-Host "Grantee: $grantee"

foreach ($dir in $folders) {
  if (-not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Write-Host "Created: $dir" -ForegroundColor Green
  } else {
    Write-Host "Exists:  $dir" -ForegroundColor DarkGray
  }
  & icacls $dir /grant "${grantee}:(OI)(CI)M" | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "icacls failed on $dir exit $LASTEXITCODE"
  }
  Write-Host "Granted Modify to $grantee on $dir" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done. Non-admin processes should now create files under those folders." -ForegroundColor Cyan
exit 0
