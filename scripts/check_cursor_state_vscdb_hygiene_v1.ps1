#Requires -Version 5.1
<#
.SYNOPSIS
  Cursor host hygiene — state.vscdb / backup / corrupt.bak size + memory pressure.

.DESCRIPTION
  Always writes reports/cursor_host_hygiene_latest.json.
  When degraded, also writes reports/cursor_perf_degraded.json and exits 1
  so solo_ops can set last_ok=false.

.NOTES
  Does not modify Cursor files. SSOT for resume-pack reload banner.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [double]$WarnVscdbGB = 30,
    [double]$WarnBackupGB = 10,
    [double]$WarnCommittedPct = 85,
    [double]$WarnRamUsedPct = 85
)

$ErrorActionPreference = "Stop"

$watchPath = Join-Path $WorkspaceRoot "docs\final\artifacts\commander_cursor_host_watch_v1_latest.json"
if (Test-Path -LiteralPath $watchPath) {
    try {
        $watch = Get-Content -LiteralPath $watchPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $override = $watch.warn_vscdb_gb_override
        if ($null -ne $override -and [double]$override -gt 0) {
            $WarnVscdbGB = [double]$override
        }
    } catch {
        # ignore parse errors — keep default WarnVscdbGB
    }
}

function Get-FileSizeGB {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    return [math]::Round((Get-Item -LiteralPath $Path).Length / 1GB, 3)
}

$globalDir = Join-Path $env:USERPROFILE "AppData\Roaming\Cursor\User\globalStorage"
$vscdb = Join-Path $globalDir "state.vscdb"
$backup = Join-Path $globalDir "state.vscdb.backup"
$corruptFiles = @()
if (Test-Path -LiteralPath $globalDir) {
    $corruptFiles = @(Get-ChildItem -LiteralPath $globalDir -Filter "state.vscdb*.corrupt.bak" -File -ErrorAction SilentlyContinue)
}

$vscdbGb = Get-FileSizeGB $vscdb
$backupGb = Get-FileSizeGB $backup
$corruptGb = 0.0
foreach ($f in $corruptFiles) {
    $corruptGb += $f.Length / 1GB
}
$corruptGb = [math]::Round($corruptGb, 3)

$cursorRunning = $null -ne (Get-Process -Name "Cursor" -ErrorAction SilentlyContinue | Select-Object -First 1)

$os = Get-CimInstance Win32_OperatingSystem
$ramUsedPct = [math]::Round(
    100 * ($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize,
    1
)
$committedPct = $null
try {
    $committedPct = [math]::Round((Get-Counter '\Memory\% Committed Bytes In Use' -ErrorAction Stop).CounterSamples.CookedValue, 1)
} catch {
    $committedPct = $null
}

$reasons = [System.Collections.Generic.List[string]]::new()
if ($null -ne $vscdbGb -and $vscdbGb -ge $WarnVscdbGB) {
    $reasons.Add(("state.vscdb {0}GB >= warn {1}GB" -f $vscdbGb, $WarnVscdbGB))
}
if ($null -ne $backupGb -and $backupGb -ge $WarnBackupGB) {
    $reasons.Add(("state.vscdb.backup {0}GB >= warn {1}GB" -f $backupGb, $WarnBackupGB))
}
if ($corruptFiles.Count -gt 0) {
    $reasons.Add(("corrupt.bak files={0} total={1}GB" -f $corruptFiles.Count, $corruptGb))
}
if ($null -ne $committedPct -and $committedPct -ge $WarnCommittedPct) {
    $reasons.Add(("committed_memory {0}% >= warn {1}%" -f $committedPct, $WarnCommittedPct))
}
if ($ramUsedPct -ge $WarnRamUsedPct) {
    $reasons.Add(("ram_used {0}% >= warn {1}%" -f $ramUsedPct, $WarnRamUsedPct))
}

$reloadRequired = $false
$mcpGatePath = Join-Path $WorkspaceRoot "reports\mcp_plugin_tool_budget_gate_latest.json"
if (Test-Path -LiteralPath $mcpGatePath) {
    try {
        $mcpGate = Get-Content -LiteralPath $mcpGatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($mcpGate.over_budget_after -eq $true) {
            $reasons.Add("mcp_plugin_tool_count over budget after diet")
            $reloadRequired = $true
        }
        if ($mcpGate.remediated -eq $true) {
            $reloadRequired = $true
        }
    } catch {
        # ignore parse errors
    }
}

$degraded = $reasons.Count -gt 0
if ($degraded) { $reloadRequired = $true }

$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$payload = [ordered]@{
    schema               = "cursor_host_hygiene_v1"
    generated_at_utc     = $utc
    cursor_running       = [bool]$cursorRunning
    global_storage_dir   = $globalDir
    files_gb             = [ordered]@{
        state_vscdb        = $vscdbGb
        state_vscdb_backup = $backupGb
        corrupt_bak_total  = $corruptGb
        corrupt_bak_count  = $corruptFiles.Count
    }
    memory               = [ordered]@{
        ram_used_pct       = $ramUsedPct
        committed_pct      = $committedPct
    }
    thresholds           = [ordered]@{
        warn_vscdb_gb      = $WarnVscdbGB
        warn_backup_gb     = $WarnBackupGB
        warn_committed_pct = $WarnCommittedPct
        warn_ram_used_pct  = $WarnRamUsedPct
    }
    degraded             = $degraded
    reload_required      = [bool]$reloadRequired
    reasons              = @($reasons)
    verify_command       = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_cursor_state_vscdb_hygiene_v1.ps1"
    janitor_command      = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CursorStateVscdbJanitor_v1.ps1 -Apply"
}

$reportDir = Join-Path $WorkspaceRoot "reports"
if (-not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}

$hygienePath = Join-Path $reportDir "cursor_host_hygiene_latest.json"
$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $hygienePath -Encoding UTF8
Write-Host "WROTE: $hygienePath"

if ($degraded) {
    $degradedPayload = [ordered]@{
        schema           = "cursor_perf_degraded_v1"
        generated_at_utc = $utc
        degraded         = $true
        reload_required  = [bool]$reloadRequired
        reasons          = @($reasons)
        hygiene_json     = "reports/cursor_host_hygiene_latest.json"
    }
    $degradedPath = Join-Path $reportDir "cursor_perf_degraded.json"
    $degradedPayload | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $degradedPath -Encoding UTF8
    Write-Host "WROTE: $degradedPath"
    Write-Host "CURSOR_HOST_HYGIENE=DEGRADED"
    exit 1
}

$staleDegraded = Join-Path $reportDir "cursor_perf_degraded.json"
if (Test-Path -LiteralPath $staleDegraded) {
    Remove-Item -LiteralPath $staleDegraded -Force -ErrorAction SilentlyContinue
}

Write-Host "CURSOR_HOST_HYGIENE=OK"
exit 0
