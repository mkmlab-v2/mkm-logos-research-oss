# Restore Cursor dogfood snapshot from reports/cursor_dogfood_rollback_snapshot_v1/manifest_latest.json
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$manifestPath = Join-Path $WorkspaceRoot "reports\cursor_dogfood_rollback_snapshot_v1\manifest_latest.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Error "No snapshot manifest. Run Invoke-CursorDogfoodSafetyBaseline_v1.ps1 first."
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$filesDir = $manifest.files_dir
if (-not (Test-Path -LiteralPath $filesDir)) {
    Write-Error "Snapshot files_dir missing: $filesDir"
}

$restored = 0
foreach ($entry in $manifest.copied_files) {
    $rel = $entry.path_rel -replace '/', '\'
    $backup = Join-Path $filesDir $entry.backup_name
    $dest = Join-Path $WorkspaceRoot $rel
    if (-not (Test-Path -LiteralPath $backup)) {
        Write-Host "SKIP missing backup: $($entry.backup_name)" -ForegroundColor Yellow
        continue
    }
    if ($WhatIfOnly) {
        Write-Host "[WhatIf] restore $rel <- $($entry.backup_name)"
        continue
    }
    $destParent = Split-Path -Parent $dest
    if ($destParent -and -not (Test-Path -LiteralPath $destParent)) {
        New-Item -ItemType Directory -Path $destParent -Force | Out-Null
    }
    Copy-Item -LiteralPath $backup -Destination $dest -Force
    $restored++
    Write-Host "RESTORED: $rel"
}

if ($WhatIfOnly) {
    Write-Host "CURSOR_DOGFOOD_ROLLBACK_WHATIF=1"
    exit 0
}

Write-Host "CURSOR_DOGFOOD_ROLLBACK_OK=1 restored=$restored label=$($manifest.label) git_at_snapshot=$($manifest.git_head)"
exit 0
