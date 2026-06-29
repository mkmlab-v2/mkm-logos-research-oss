#Requires -Version 5.1
<#
.SYNOPSIS
  Backup Cursor state.vscdb (+ wal/shm) while Cursor may be running.

.NOTES
  Large (~57GB) — uses robocopy. Writes reports/cursor_state_vscdb_backup_manifest_latest.json
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$BackupRoot = ""
)

$ErrorActionPreference = "Stop"
$globalDir = Join-Path $env:USERPROFILE "AppData\Roaming\Cursor\User\globalStorage"
$vscdb = Join-Path $globalDir "state.vscdb"
if (-not (Test-Path -LiteralPath $vscdb)) {
    Write-Host "FAIL: state.vscdb not found at $vscdb"
    exit 2
}

if (-not $BackupRoot) {
    function Test-BackupDriveCandidate {
        param([string]$ParentPath, [double]$MinFreeGB = 70)
        if (-not (Test-Path -LiteralPath $ParentPath)) {
            try { New-Item -ItemType Directory -Path $ParentPath -Force | Out-Null } catch { return $false }
        }
        $driveLetter = $ParentPath.Substring(0, 1)
        $ps = Get-PSDrive -Name $driveLetter -ErrorAction SilentlyContinue
        if (-not $ps -or $ps.Free -le ($MinFreeGB * 1GB)) { return $false }
        $probe = Join-Path $ParentPath (".write_probe_{0}" -f [guid]::NewGuid().ToString("N"))
        try {
            [IO.File]::WriteAllText($probe, "ok")
            Remove-Item -LiteralPath $probe -Force
            return $true
        } catch {
            return $false
        }
    }

    $candidates = @(
        "F:\BACKUP\cursor_state_vscdb_{0}",
        "E:\BACKUP\cursor_state_vscdb_{0}"
    )
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    foreach ($pattern in $candidates) {
        $parent = Split-Path ($pattern -f $stamp) -Parent
        if (Test-BackupDriveCandidate -ParentPath $parent) {
            $BackupRoot = $pattern -f $stamp
            break
        }
    }
}
if (-not $BackupRoot) {
    Write-Host "FAIL: no writable backup destination with ~70GB free (F:\BACKUP or E:\BACKUP; set -BackupRoot manually)"
    Write-Host "NOTE: C:\workspace\storage\MKM_BACKUP is no longer an automatic fallback — use F:\BACKUP"
    exit 2
}

New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
$started = Get-Date

$files = @("state.vscdb", "state.vscdb-wal", "state.vscdb-shm")
$copied = @()
foreach ($name in $files) {
    $src = Join-Path $globalDir $name
    if (-not (Test-Path -LiteralPath $src)) { continue }
    Write-Host "Copying $name ..."
    robocopy $globalDir $BackupRoot $name /R:2 /W:5 /NP /NFL /NDL | Out-Null
    if ($LASTEXITCODE -ge 8) {
        Write-Host "FAIL: robocopy $name exit $LASTEXITCODE"
        exit 1
    }
    $copied += $name
}

$rows = foreach ($name in $copied) {
    $p = Join-Path $BackupRoot $name
    [ordered]@{
        name = $name
        gb   = [math]::Round((Get-Item -LiteralPath $p).Length / 1GB, 3)
    }
}

$mainBackup = Join-Path $BackupRoot "state.vscdb"
$backupOk = (Test-Path -LiteralPath $mainBackup) -and ((Get-Item -LiteralPath $mainBackup).Length -gt 1GB)

$manifest = [ordered]@{
    schema           = "cursor_state_vscdb_backup_manifest_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    backup_dir       = $BackupRoot
    source_dir       = $globalDir
    files            = @($rows)
    backup_ok        = $backupOk
    elapsed_sec      = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)
    finish_command   = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CursorStateVscdbResetAfterBackup_v1.ps1"
}

$reportDir = Join-Path $WorkspaceRoot "reports"
if (-not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}
$manifestPath = Join-Path $reportDir "cursor_state_vscdb_backup_manifest_latest.json"
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Write-Host ""
Write-Host ("BACKUP ok={0} dir={1}" -f $backupOk, $BackupRoot)
Write-Host "WROTE: $manifestPath"
Write-Host ""
Write-Host "NEXT (after you QUIT Cursor completely):"
Write-Host "  cd C:\workspace"
Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CursorStateVscdbResetAfterBackup_v1.ps1"
exit $(if ($backupOk) { 0 } else { 1 })
