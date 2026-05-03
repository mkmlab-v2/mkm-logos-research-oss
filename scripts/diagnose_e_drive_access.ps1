#Requires -Version 5.1
# Read-only diagnosis for E: — no ACL changes
$ErrorActionPreference = 'Continue'
Write-Host "=== E: drive diagnosis ===" -ForegroundColor Cyan
Write-Host "User: $([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)"
Write-Host "Elevated: $(
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  $p = New-Object Security.Principal.WindowsPrincipal($id)
  $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
)"
try {
  $v = Get-Volume -DriveLetter E -ErrorAction Stop
  Write-Host "FileSystem: $($v.FileSystemType)  Health: $($v.HealthStatus)  SizeGB: $([math]::Round($v.Size/1GB,2))"
} catch { Write-Host "Get-Volume E: $_" -ForegroundColor Yellow }
try {
  $d = New-Object System.IO.DriveInfo('E')
  Write-Host "DriveType: $($d.DriveType)  IsReady: $($d.IsReady)  Label: $($d.VolumeLabel)"
} catch { }
$root = 'E:\'
if (Test-Path -LiteralPath $root) {
  $item = Get-Item -LiteralPath $root -Force
  Write-Host "E:\ Attributes: $($item.Attributes)"
}
Write-Host ""
Write-Host "icacls E:\ (first 25 lines):" -ForegroundColor DarkCyan
& icacls 'E:\' 2>&1 | Select-Object -First 25
Write-Host ""
Write-Host "Test: create E:\_mkm_acl_test (should fail if same as before)" -ForegroundColor DarkCyan
try {
  $t = 'E:\_mkm_acl_test'
  if (Test-Path $t) { Remove-Item $t -Recurse -Force -ErrorAction SilentlyContinue }
  New-Item -ItemType Directory -Path $t -Force -ErrorAction Stop | Out-Null
  Remove-Item $t -Recurse -Force
  Write-Host "RESULT: E:\ root IS writable" -ForegroundColor Green
} catch {
  Write-Host "RESULT: E:\ root NOT writable — $($_.Exception.Message)" -ForegroundColor Red
}
