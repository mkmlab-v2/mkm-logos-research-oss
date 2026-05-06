param(
    [int]$TopN = 12,
    [int]$WarnCursorTotalMB = 6500,
    [int]$WarnRendererMaxMB = 1500,
    [double]$WarnRamUsedPct = 80.0,
    [switch]$FailOnWarn
)

$ErrorActionPreference = "Stop"

function Get-RamSummary {
    $os = Get-CimInstance Win32_OperatingSystem
    $totalGb = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    $freeGb = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
    $usedPct = [math]::Round(
        100 * ($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize,
        1
    )
    return [PSCustomObject]@{
        TotalGB = $totalGb
        FreeGB = $freeGb
        UsedPct = $usedPct
    }
}

function Get-CursorProcesses {
    return Get-CimInstance Win32_Process |
        Where-Object { $_.Name -ieq "Cursor.exe" } |
        ForEach-Object {
            $proc = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
            $type = if ($_.CommandLine -match '--type=([^\s"]+)') {
                $Matches[1]
            } else {
                "browser(main)"
            }
            [PSCustomObject]@{
                PID = $_.ProcessId
                Type = $type
                WS_MB = if ($proc) { [math]::Round($proc.WorkingSet64 / 1MB, 0) } else { 0 }
                CPU_s = if ($proc) { [math]::Round($proc.CPU, 1) } else { 0 }
            }
        }
}

$ram = Get-RamSummary
$cursor = Get-CursorProcesses
$cursorCount = ($cursor | Measure-Object).Count
$cursorTotalMb = if ($cursorCount -gt 0) {
    [math]::Round(($cursor | Measure-Object WS_MB -Sum).Sum, 0)
} else {
    0
}

Write-Output ("RAM_Total_GB={0} RAM_Free_GB={1} RAM_Used_Pct={2}" -f $ram.TotalGB, $ram.FreeGB, $ram.UsedPct)
Write-Output ("Cursor_count={0} Cursor_total_MB={1}" -f $cursorCount, $cursorTotalMb)

$renderers = if ($cursorCount -gt 0) { $cursor | Where-Object { $_.Type -eq "renderer" } } else { @() }
$maxRendererMb = if (($renderers | Measure-Object).Count -gt 0) {
    [math]::Round(($renderers | Measure-Object WS_MB -Maximum).Maximum, 0)
} else {
    0
}

$warnings = @()
if ($ram.UsedPct -ge $WarnRamUsedPct) {
    $warnings += ("RAM high: {0}% >= {1}%" -f $ram.UsedPct, $WarnRamUsedPct)
}
if ($cursorTotalMb -ge $WarnCursorTotalMB) {
    $warnings += ("Cursor total high: {0}MB >= {1}MB" -f $cursorTotalMb, $WarnCursorTotalMB)
}
if ($maxRendererMb -ge $WarnRendererMaxMB) {
    $warnings += ("Renderer high: {0}MB >= {1}MB" -f $maxRendererMb, $WarnRendererMaxMB)
}

if ($warnings.Count -gt 0) {
    Write-Output ""
    Write-Output "[WARN]"
    $warnings | ForEach-Object { Write-Output ("- {0}" -f $_) }
    Write-Output "Health=WARNING"
} else {
    Write-Output "Health=OK"
}

if ($cursorCount -eq 0) {
    Write-Output "No Cursor.exe process found."
    if ($FailOnWarn -and $warnings.Count -gt 0) {
        exit 1
    }
    exit 0
}

Write-Output ""
Write-Output ("Top {0} Cursor processes by memory" -f $TopN)
$cursor |
    Sort-Object WS_MB -Descending |
    Select-Object -First $TopN PID, Type, WS_MB, CPU_s |
    Format-Table -AutoSize

Write-Output ""
Write-Output "Cursor memory by process type"
$cursor |
    Group-Object Type |
    ForEach-Object {
        [PSCustomObject]@{
            Type = $_.Name
            Count = ($_.Group | Measure-Object).Count
            Total_MB = [math]::Round(($_.Group | Measure-Object WS_MB -Sum).Sum, 0)
            Max_MB = [math]::Round(($_.Group | Measure-Object WS_MB -Maximum).Maximum, 0)
        }
    } |
    Sort-Object Total_MB -Descending |
    Format-Table -AutoSize

if ($FailOnWarn -and $warnings.Count -gt 0) {
    exit 1
}
