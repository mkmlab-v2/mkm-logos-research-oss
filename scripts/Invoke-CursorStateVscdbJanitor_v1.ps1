#Requires -Version 5.1
<#
.SYNOPSIS
  Safe Cursor globalStorage janitor — corrupt.bak and backup only.

.DESCRIPTION
  Never deletes state.vscdb main. Skips when Cursor.exe is running.
  Default is report-only; pass -Apply to delete safe waste files.

.PARAMETER Apply
  Perform deletion (only when Cursor is not running).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

$globalDir = Join-Path $env:USERPROFILE "AppData\Roaming\Cursor\User\globalStorage"
if (-not (Test-Path -LiteralPath $globalDir)) {
    Write-Host "SKIP: globalStorage missing"
    exit 0
}

$cursorRunning = $null -ne (Get-Process -Name "Cursor" -ErrorAction SilentlyContinue | Select-Object -First 1)
if ($cursorRunning) {
    Write-Host "SKIP: Cursor.exe running — janitor will not delete"
    $payload = [ordered]@{
        schema           = "cursor_state_vscdb_janitor_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        skipped          = $true
        skip_reason      = "cursor_running"
        apply            = [bool]$Apply
    }
    $out = Join-Path $WorkspaceRoot "reports\cursor_state_vscdb_janitor_latest.json"
    $payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $out -Encoding UTF8
    exit 2
}

$candidates = @()
$candidates += Get-ChildItem -LiteralPath $globalDir -Filter "state.vscdb*.corrupt.bak" -File -ErrorAction SilentlyContinue
$backup = Join-Path $globalDir "state.vscdb.backup"
if (Test-Path -LiteralPath $backup) {
    $candidates += Get-Item -LiteralPath $backup
}

$rows = foreach ($f in $candidates) {
    [ordered]@{
        name    = $f.Name
        size_gb = [math]::Round($f.Length / 1GB, 3)
        deleted = $false
    }
}

$deletedGb = 0.0
if ($Apply) {
    foreach ($f in $candidates) {
        $size = $f.Length
        Remove-Item -LiteralPath $f.FullName -Force
        $deletedGb += $size / 1GB
        foreach ($row in $rows) {
            if ($row.name -eq $f.Name) { $row.deleted = $true }
        }
    }
}

$report = [ordered]@{
    schema           = "cursor_state_vscdb_janitor_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    skipped          = $false
    apply            = [bool]$Apply
    cursor_running   = $false
    candidates       = @($rows)
    deleted_gb       = [math]::Round($deletedGb, 3)
    note             = "state.vscdb main is never deleted by this janitor"
    verify_command   = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CursorStateVscdbJanitor_v1.ps1 -Apply"
}

$out = Join-Path $WorkspaceRoot "reports\cursor_state_vscdb_janitor_latest.json"
$reportDir = Split-Path -Parent $out
if (-not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $out -Encoding UTF8
Write-Host "WROTE: $out"
Write-Host ("JANITOR candidates={0} deleted_gb={1} apply={2}" -f $candidates.Count, $report.deleted_gb, $Apply.IsPresent)
exit 0
