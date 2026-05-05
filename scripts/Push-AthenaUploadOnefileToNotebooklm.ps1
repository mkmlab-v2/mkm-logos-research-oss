<#
.SYNOPSIS
  Build ATHENA upload onefile and push to NotebookLM as a single source.

.DESCRIPTION
  1) Regenerates docs/final/artifacts/ATHENA_UPLOAD_ONEFILE_LATEST.md
  2) Deletes previous source entries with the same title (unless -KeepHistory)
  3) Uploads latest content with fixed title for deterministic retrieval.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$NotebookId = "347e5cbe-0ade-4615-9aac-8747d4fa644e",
    [string]$SourceTitle = "ATHENA_UPLOAD_ONEFILE_LATEST",
    [string]$LogPath = "C:\workspace\reports\athena_upload_onefile_push.log",
    [switch]$KeepHistory
)

$ErrorActionPreference = "Stop"

$builder = Join-Path $WorkspaceRoot "scripts\build_athena_upload_onefile_latest.py"
$payload = Join-Path $WorkspaceRoot "docs\final\artifacts\ATHENA_UPLOAD_ONEFILE_LATEST.md"

if (-not (Test-Path -LiteralPath $builder)) {
    throw "Builder not found: $builder"
}

if (-not (Test-Path -LiteralPath (Split-Path -Parent $LogPath))) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $LogPath) -Force | Out-Null
}

function Write-Log([string]$m) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $m"
    $line | Tee-Object -FilePath $LogPath -Append
}

Write-Log "=== START Push-AthenaUploadOnefileToNotebooklm ==="
Write-Log "workspace=$WorkspaceRoot notebook_id=$NotebookId title=$SourceTitle keep_history=$KeepHistory"

# Step 1: rebuild payload
& py "$builder" 2>&1 | Tee-Object -FilePath $LogPath -Append
if ($LASTEXITCODE -ne 0) {
    Write-Log "FAIL builder_exit=$LASTEXITCODE"
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $payload)) {
    Write-Log "FAIL payload_missing: $payload"
    exit 1
}

$content = [System.IO.File]::ReadAllText($payload, [System.Text.UTF8Encoding]::new($false))
if ([string]::IsNullOrWhiteSpace($content)) {
    Write-Log "FAIL payload_empty: $payload"
    exit 1
}

# Step 2: remove old same-title sources unless KeepHistory
if (-not $KeepHistory) {
    try {
        $raw = (& nlm source list $NotebookId 2>&1 | Out-String)
        $list = $raw | ConvertFrom-Json
        $dups = @($list | Where-Object { $_.title -eq $SourceTitle })
        if ($dups.Count -gt 0) {
            $ids = @($dups | ForEach-Object { $_.id })
            Write-Log ("deleting_existing_count={0}" -f $ids.Count)
            & nlm source delete @ids --confirm 2>&1 | Tee-Object -FilePath $LogPath -Append
        } else {
            Write-Log "deleting_existing_count=0"
        }
    } catch {
        Write-Log "WARN source_list_or_delete_failed: $_"
    }
}

# Step 3: upload new source from file (stable for markdown payload)
& nlm source add $NotebookId --file $payload --title $SourceTitle --wait 2>&1 | Tee-Object -FilePath $LogPath -Append
if ($LASTEXITCODE -ne 0) {
    Write-Log "FAIL upload_exit=$LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Log "OK upload_complete title=$SourceTitle"
Write-Log "=== END Push-AthenaUploadOnefileToNotebooklm ==="
exit 0

