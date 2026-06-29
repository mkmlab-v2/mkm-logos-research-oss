#Requires -Version 5.1
<#
.SYNOPSIS
  Finish state.vscdb cleanup AFTER backup — Cursor must be fully closed.

.DESCRIPTION
  1) Verify backup manifest exists
  2) Refuse if Cursor.exe is running
  3) Rename state.vscdb (+ wal/shm) so Cursor creates fresh DB on next start
  4) Run safe janitor + hygiene check

  Backup is NOT done by this script — run Invoke-CursorStateVscdbBackup_v1.ps1 first.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$manifestPath = Join-Path $WorkspaceRoot "reports\cursor_state_vscdb_backup_manifest_latest.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Host "FAIL: backup manifest missing — run Invoke-CursorStateVscdbBackup_v1.ps1 first"
    exit 2
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $manifest.backup_ok) {
    Write-Host "FAIL: backup_ok=false in manifest"
    exit 2
}

$cursorRunning = $null -ne (Get-Process -Name "Cursor" -ErrorAction SilentlyContinue | Select-Object -First 1)
if ($cursorRunning) {
    Write-Host "FAIL: Cursor.exe still running — quit Cursor completely (Task Manager) then re-run."
    exit 3
}

$globalDir = Join-Path $env:USERPROFILE "AppData\Roaming\Cursor\User\globalStorage"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$renamed = @()

foreach ($name in @("state.vscdb", "state.vscdb-wal", "state.vscdb-shm")) {
    $path = Join-Path $globalDir $name
    if (Test-Path -LiteralPath $path) {
        $dest = Join-Path $globalDir ("{0}.old_{1}" -f $name, $stamp)
        Rename-Item -LiteralPath $path -NewName (Split-Path -Leaf $dest) -Force
        $renamed += (Split-Path -Leaf $dest)
    }
}

$janitor = Join-Path $WorkspaceRoot "scripts\Invoke-CursorStateVscdbJanitor_v1.ps1"
if (Test-Path -LiteralPath $janitor) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $janitor -WorkspaceRoot $WorkspaceRoot -Apply | Out-Host
}

$hygiene = Join-Path $WorkspaceRoot "scripts\check_cursor_state_vscdb_hygiene_v1.ps1"
$hygieneExit = 0
if (Test-Path -LiteralPath $hygiene) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $hygiene -WorkspaceRoot $WorkspaceRoot | Out-Host
    $hygieneExit = $LASTEXITCODE
}

$out = Join-Path $WorkspaceRoot "reports\cursor_state_vscdb_reset_latest.json"
$payload = [ordered]@{
    schema           = "cursor_state_vscdb_reset_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    backup_manifest  = "reports/cursor_state_vscdb_backup_manifest_latest.json"
    backup_dir       = $manifest.backup_dir
    renamed_files    = @($renamed)
    next_step        = "Start Cursor — fresh state.vscdb will be created"
    restore_hint     = "Copy backup state.vscdb back to globalStorage (Cursor closed)"
}
$payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $out -Encoding UTF8

Write-Host ""
Write-Host "OK: reset complete. Renamed: $($renamed -join ', ')"
Write-Host "WROTE: $out"
Write-Host "NEXT: Start Cursor normally."
exit $(if ($hygieneExit -eq 0) { 0 } else { 0 })
