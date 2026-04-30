param(
    [int[]]$Ports = @(3010, 5678),
    [switch]$IncludeNpxMcp,
    [switch]$DryRun
)

$ErrorActionPreference = "SilentlyContinue"

function Stop-ListenerByPort([int]$Port, [switch]$DryRunMode) {
    $listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    if ($listeners.Count -eq 0) {
        Write-Host "[port:$Port] no listener"
        return 0
    }

    $stopped = 0
    $pids = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($procId in $pids) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        $name = if ($proc) { $proc.ProcessName } else { "unknown" }
        if ($DryRunMode) {
            Write-Host "[port:$Port] would stop PID=$procId ($name)"
        } else {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Write-Host "[port:$Port] stopped PID=$procId ($name)"
        }
        $stopped++
    }
    return $stopped
}

function Stop-CimByPattern([string]$Pattern, [string]$Label, [switch]$DryRunMode) {
    $hits = @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -and $_.CommandLine -match $Pattern }
    )

    if ($hits.Count -eq 0) {
        Write-Host "[$Label] no match"
        return 0
    }

    $stopped = 0
    foreach ($p in $hits) {
        if ($DryRunMode) {
            Write-Host "[$Label] would stop PID=$($p.ProcessId)"
        } else {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Host "[$Label] stopped PID=$($p.ProcessId)"
        }
        $stopped++
    }
    return $stopped
}

$totalStopped = 0
foreach ($port in $Ports) {
    $totalStopped += Stop-ListenerByPort -Port $port -DryRunMode:$DryRun
}

# Common local dev launch patterns in this workspace.
$totalStopped += Stop-CimByPattern -Pattern "next\dist\\bin\\next.*\sdev(\s|$)" -Label "next-dev" -DryRunMode:$DryRun
$totalStopped += Stop-CimByPattern -Pattern "\\bn8n(\.cmd)?\b.*\bstart\b" -Label "n8n-start" -DryRunMode:$DryRun

if ($IncludeNpxMcp) {
    $totalStopped += Stop-CimByPattern -Pattern "@modelcontextprotocol|cursor-mobile-bridge" -Label "npx-mcp" -DryRunMode:$DryRun
}

Write-Output "[summary] stopped=$totalStopped dry_run=$($DryRun.IsPresent)"
