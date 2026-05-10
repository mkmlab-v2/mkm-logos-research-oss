<#
.SYNOPSIS
  live_sync/incoming/daemon_alive_check.json 신선도 검사 → reports/live_sync_heartbeat_check_latest.json

.DESCRIPTION
  기본: 파일 없음 → skipped (exit 0). -RequireHeartbeat 시 없음/오래됨 → exit 1.
  오래됨은 MaxAgeSeconds 초과.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LiveSyncHeartbeatCheck.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LiveSyncHeartbeatCheck.ps1 -RequireHeartbeat -MaxAgeSeconds 300
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [string]$RelativePath = "live_sync\incoming\daemon_alive_check.json",
    [int]$MaxAgeSeconds = 600,
    [switch]$RequireHeartbeat,
    [switch]$StrictExit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$jsonPath = Join-Path $WorkspaceRoot $RelativePath
$outReport = Join-Path $WorkspaceRoot "reports\live_sync_heartbeat_check_latest.json"

function Read-Json([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try { return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json }
    catch { return $null }
}

$payload = Read-Json -Path $jsonPath
$ts = $null
if ($payload) {
    if ($payload.generated_at_utc) { $ts = "$($payload.generated_at_utc)" }
    elseif ($payload.ts_utc) { $ts = "$($payload.ts_utc)" }
}

$ageSec = $null
$fresh = $false
if (-not [string]::IsNullOrWhiteSpace($ts)) {
    try {
        $dto = [datetimeoffset]::Parse($ts)
        $ageSec = [math]::Round(([datetimeoffset]::UtcNow - $dto.ToUniversalTime()).TotalSeconds, 3)
        $fresh = ($ageSec -le $MaxAgeSeconds)
    }
    catch {
        $ageSec = $null
        $fresh = $false
    }
}

$status = if (-not (Test-Path -LiteralPath $jsonPath)) {
        if ($RequireHeartbeat) { "missing_required" } else { "missing_skipped" }
    }
    elseif ($null -eq $ts) { "invalid_timestamp" }
    elseif ($null -eq $ageSec) { "parse_error" }
    elseif ($fresh) { "fresh" }
    else { "stale" }

$fail = ($status -eq "stale" -or $status -eq "invalid_timestamp" -or $status -eq "parse_error" -or $status -eq "missing_required")

$report = [ordered]@{
    schema           = "live_sync_heartbeat_check_v1"
    checked_at_utc     = [datetime]::UtcNow.ToString("o")
    workspace_root     = $WorkspaceRoot
    heartbeat_path     = $jsonPath
    max_age_seconds    = $MaxAgeSeconds
    require_heartbeat  = [bool]$RequireHeartbeat
    heartbeat_schema   = if ($payload -and $payload.schema) { "$($payload.schema)" } else { $null }
    age_seconds        = $ageSec
    fresh              = $fresh
    status             = $status
}

if (-not (Test-Path -LiteralPath (Split-Path -Parent $outReport))) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $outReport) -Force | Out-Null
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outReport -Encoding UTF8
Write-Output "live_sync_heartbeat_check_written=$outReport status=$status"

$exitCode = 0
if ($fail) {
    $exitCode = 1
}
if ($StrictExit -and ($status -eq "missing_skipped")) {
    $exitCode = 1
}

exit $exitCode
