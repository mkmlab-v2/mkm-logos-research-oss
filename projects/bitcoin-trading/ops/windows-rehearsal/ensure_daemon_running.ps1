param(
    [int]$StaleMinutes = 15,
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$memoryDir = Join-Path $projectRoot "memory"
$heartbeatPath = Join-Path $memoryDir "trading_daemon_heartbeat.txt"
$stopPath = Join-Path $memoryDir "STOP.txt"
$logPath = Join-Path $memoryDir "watchdog_direct.log"
$daemonArg = "scripts/start_24h_daemon.py"

if (-not (Test-Path $memoryDir)) {
    New-Item -ItemType Directory -Path $memoryDir | Out-Null
}

function Write-Log([string]$message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
    Add-Content -Path $logPath -Value $line
    Write-Host $line
}

function Get-DaemonProcesses {
    # Do not filter Win32_Process.Name='python.exe' here: some shells report differently;
    # match by script path in CommandLine only.
    Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -and ($_.CommandLine -match 'start_24h_daemon\.py') }
}

function Start-Daemon {
    if ($NoStart) {
        Write-Log "NoStart mode: start skipped"
        return
    }

    Write-Log "Starting daemon process"
    Start-Process -FilePath "python" -ArgumentList $daemonArg -WorkingDirectory $projectRoot -WindowStyle Hidden
}

if (Test-Path $stopPath) {
    Write-Log "STOP.txt exists. Ensuring daemon is not running."
    $procs = Get-DaemonProcesses
    foreach ($p in $procs) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Log "Stopped daemon PID=$($p.ProcessId) due to kill switch"
    }
    exit 0
}

$daemonProcs = Get-DaemonProcesses
# If multiple daemons exist (manual restart + watchdog, etc.), keep the newest only.
if ($daemonProcs.Count -gt 1) {
    Write-Log ("Multiple daemon processes detected: {0}. Keeping newest." -f $daemonProcs.Count)
    $sorted = @($daemonProcs | Sort-Object CreationDate -Descending)
    $keepPid = $sorted[0].ProcessId
    foreach ($p in $sorted | Select-Object -Skip 1) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Log ("Stopped duplicate daemon PID={0} (keeping PID={1})" -f $p.ProcessId, $keepPid)
    }
    # Win32_Process (CIM) can briefly return an empty list right after Stop-Process; retry before starting a second copy.
    Start-Sleep -Seconds 4
    $daemonProcs = Get-DaemonProcesses
    if ($daemonProcs.Count -eq 0 -and (Get-Process -Id $keepPid -ErrorAction SilentlyContinue)) {
        for ($i = 0; $i -lt 15; $i++) {
            $daemonProcs = Get-DaemonProcesses
            if ($daemonProcs.Count -gt 0) { break }
            Start-Sleep -Milliseconds 400
        }
    }
    if ($daemonProcs.Count -eq 0 -and (Get-Process -Id $keepPid -ErrorAction SilentlyContinue)) {
        Write-Log ("Survivor PID={0} still alive after dedupe; CIM list lag — not starting another daemon." -f $keepPid)
        Write-Log "Daemon healthy"
        exit 0
    }
}
$isRunning = $daemonProcs.Count -gt 0
$heartbeatStale = $true

if (Test-Path $heartbeatPath) {
    try {
        $ts = (Get-Content $heartbeatPath -Raw).Trim()
        if ($ts) {
            $hb = [datetime]::Parse($ts)
            $ageMin = ((Get-Date) - $hb).TotalMinutes
            $heartbeatStale = $ageMin -gt $StaleMinutes
            Write-Log ("Heartbeat age={0:N1} min (threshold={1})" -f $ageMin, $StaleMinutes)
        }
    } catch {
        Write-Log "Heartbeat parse failed: $($_.Exception.Message)"
    }
} else {
    Write-Log "Heartbeat file missing"
}

if (-not $isRunning) {
    # If WMI/CIM cannot see python.exe (policy/sandbox) but heartbeat is fresh, do not spawn a second copy.
    $hbYoung = $false
    if (Test-Path $heartbeatPath) {
        try {
            $ts = (Get-Content $heartbeatPath -Raw).Trim()
            if ($ts) {
                $hb = [datetime]::Parse($ts)
                $ageMin = ((Get-Date) - $hb).TotalMinutes
                $hbYoung = $ageMin -le $StaleMinutes
            }
        } catch {
            $hbYoung = $false
        }
    }
    if ($hbYoung) {
        Write-Log "Daemon not listed by process query but heartbeat is fresh — not starting another daemon."
        Write-Log "Daemon healthy"
        exit 0
    }
    Write-Log "Daemon not running"
    Start-Daemon
    exit 0
}

if ($heartbeatStale) {
    Write-Log "Daemon running but heartbeat stale. Restarting."
    foreach ($p in $daemonProcs) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Log "Stopped stale daemon PID=$($p.ProcessId)"
    }
    Start-Daemon
    exit 0
}

Write-Log "Daemon healthy"
