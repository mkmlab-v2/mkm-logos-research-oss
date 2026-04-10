<#
.SYNOPSIS
  Removes terminal.integrated.cwd from Cursor User settings when the value is a Windows path (breaks SSH Remote Linux cwd).

.DESCRIPTION
  Edits only %APPDATA%\Cursor\User\settings.json (not VS Code). Backs up before change.
  Keeps values like ${workspaceFolder} or /unix/paths (only removes entries matching X:\ or X:/).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Remove-CursorWindowsTerminalCwd.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Remove-CursorWindowsTerminalCwd.ps1 -WhatIf
#>
param(
  [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$settingsPath = Join-Path $env:APPDATA "Cursor\User\settings.json"

if (-not (Test-Path -LiteralPath $settingsPath)) {
  Write-Host "Not found: $settingsPath" -ForegroundColor Yellow
  exit 0
}

$raw = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8

# Match JSON string value that looks like a Windows absolute path (E:\..., E:/...)
$pattern = '(?ms)^[ \t]*"terminal\.integrated\.cwd"\s*:\s*"[^"\r\n]*[A-Za-z]:[\\/][^"\r\n]*"\s*,?\r?\n'

$matches = [regex]::Matches($raw, $pattern)
if ($matches.Count -eq 0) {
  Write-Host "No Windows-path terminal.integrated.cwd in $settingsPath (already clean or absent)." -ForegroundColor Green
  exit 0
}

if ($WhatIf) {
  Write-Host "Would remove $($matches.Count) occurrence(s) from $settingsPath" -ForegroundColor Cyan
  foreach ($m in $matches) {
    Write-Host ("---`n" + ($m.Value.TrimEnd()) + "`n---")
  }
  exit 0
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = "${settingsPath}.bak.${stamp}"
Copy-Item -LiteralPath $settingsPath -Destination $backupPath -Force
Write-Host "Backup: $backupPath" -ForegroundColor DarkGray

$newRaw = ([regex]::Replace($raw, $pattern, '', [System.Text.RegularExpressions.RegexOptions]::Multiline)).TrimEnd()

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($settingsPath, $newRaw + "`r`n", $utf8NoBom)

Write-Host "Removed Windows-path terminal.integrated.cwd from User settings. Reload Cursor (Developer: Reload Window)." -ForegroundColor Green
