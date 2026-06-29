# Snapshot Cursor dogfood touchpoints before apply — rollback via Invoke-CursorDogfoodRollback_v1.ps1
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$Label = "cursor_dogfood_pre_apply"
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$snapRoot = Join-Path $WorkspaceRoot "reports\cursor_dogfood_rollback_snapshot_v1"
$filesDir = Join-Path $snapRoot "files"
New-Item -ItemType Directory -Path $filesDir -Force | Out-Null

$watchRel = @(
    "docs\final\artifacts\todo_queue_latest.json",
    "docs\final\artifacts\mkm_chat_resume_pack_latest.json",
    "docs\final\artifacts\mkm_chat_resume_pack_latest.md",
    "storage\meta\mkm_ops_memory_index_v1.json",
    "reports\mkm_cursor_session_upgrade_v1_latest.json"
)

$copied = @()
$missing = @()
foreach ($rel in $watchRel) {
    $src = Join-Path $WorkspaceRoot $rel
    if (-not (Test-Path -LiteralPath $src)) {
        $missing += $rel
        continue
    }
    $dest = Join-Path $filesDir ($rel -replace '[\\/]', '__')
    Copy-Item -LiteralPath $src -Destination $dest -Force
    $hash = (Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash
    $copied += [ordered]@{
        path_rel   = $rel.Replace('\', '/')
        backup_name = (Split-Path -Leaf $dest)
        sha256     = $hash
        size_bytes = (Get-Item -LiteralPath $src).Length
    }
}

$gitHead = $null
$gitDirty = $null
try {
    $gitHead = (git -C $WorkspaceRoot rev-parse HEAD 2>$null).Trim()
    $status = git -C $WorkspaceRoot status --porcelain 2>$null
    $gitDirty = [bool]($status -and $status.Trim())
} catch {
    $gitHead = "unknown"
    $gitDirty = $null
}

$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.ffffffZ")
$manifest = [ordered]@{
    schema              = "cursor_dogfood_rollback_snapshot_v1"
    label               = $Label
    generated_at_utc    = $utc
    workspace_root      = $WorkspaceRoot
    git_head            = $gitHead
    git_dirty           = $gitDirty
    snapshot_dir        = $snapRoot
    files_dir           = $filesDir
    copied_files        = $copied
    missing_at_snapshot = $missing
    rollback_command    = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CursorDogfoodRollback_v1.ps1"
    boundary_ack        = "Restores listed artifacts only; does not git reset --hard or delete new files"
}

$manifestPath = Join-Path $snapRoot "manifest_latest.json"
($manifest | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$reportCopy = Join-Path $WorkspaceRoot "reports\cursor_dogfood_rollback_manifest_v1_latest.json"
($manifest | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $reportCopy -Encoding UTF8

Write-Host "WROTE: $manifestPath"
Write-Host "WROTE: $reportCopy"
Write-Host "CURSOR_DOGFOOD_BASELINE_OK=1 copied=$($copied.Count) missing=$($missing.Count) git=$gitHead"
exit 0
