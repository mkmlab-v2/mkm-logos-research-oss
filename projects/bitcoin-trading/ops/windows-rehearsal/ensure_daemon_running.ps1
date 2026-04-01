param(
    [int]$StaleMinutes = 15,
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$memoryDir = Join-Path $projectRoot "memory"
$heartbeatPath = Join-Path $memoryDir "trading_daemon_heartbeat.txt"
$daemonStatusLegacyPath = Join-Path $memoryDir "trading_daemon_status.json"
$daemonStatusV2Dir = Join-Path $memoryDir "v2\\status"
$daemonStatusV2Path = Join-Path $daemonStatusV2Dir "trading_daemon_status.json"
$stopPath = Join-Path $memoryDir "STOP.txt"
$logPath = Join-Path $memoryDir "watchdog_direct.log"
$lockPath = Join-Path $memoryDir "daemon_singleton.lock"
$daemonArg = "scripts/start_24h_daemon.py"
$factSafeProphecyPath = Join-Path $projectRoot "..\..\docs\final\artifacts\prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
$factSafeSyncScript = Join-Path $projectRoot "..\..\scripts\sync_fact_safe_risk_profile.py"
$riskProfilePath = Join-Path $projectRoot "memory\v2\risk\risk_profile_fact_safe_latest.json"
$riskProfileSourceName = [string]$env:RISK_PROFILE_SOURCE_NAME
$riskProfileModeName = [string]$env:RISK_PROFILE_MODE_NAME

# If env overrides are absent, preserve source/mode from existing profile
# so watchdog restarts do not unintentionally downgrade n8n-tagged pipeline metadata.
if (([string]::IsNullOrWhiteSpace($riskProfileSourceName) -or [string]::IsNullOrWhiteSpace($riskProfileModeName)) -and (Test-Path $riskProfilePath)) {
    try {
        $existingProfile = Get-Content $riskProfilePath -Raw | ConvertFrom-Json
        if ([string]::IsNullOrWhiteSpace($riskProfileSourceName) -and -not [string]::IsNullOrWhiteSpace([string]$existingProfile.source)) {
            $riskProfileSourceName = [string]$existingProfile.source
        }
        if ([string]::IsNullOrWhiteSpace($riskProfileModeName) -and -not [string]::IsNullOrWhiteSpace([string]$existingProfile.mode)) {
            $riskProfileModeName = [string]$existingProfile.mode
        }
    } catch {
        # keep defaults when profile parse fails
    }
}

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

    if ((Test-Path $factSafeSyncScript) -and (Test-Path $factSafeProphecyPath)) {
        Write-Log "Syncing Fact-Safe risk profile before daemon start"
        $syncArgs = @($factSafeSyncScript, "--prophecy", $factSafeProphecyPath, "--output", $riskProfilePath)
        if (-not [string]::IsNullOrWhiteSpace($riskProfileSourceName)) {
            $syncArgs += @("--source", $riskProfileSourceName)
        }
        if (-not [string]::IsNullOrWhiteSpace($riskProfileModeName)) {
            $syncArgs += @("--mode", $riskProfileModeName)
        }
        py @syncArgs | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Log "WARN: Fact-Safe risk sync failed; daemon start continues with existing profile"
        }
    } else {
        Write-Log "Fact-Safe risk sync skipped (prophecy/script missing)"
    }

    Write-Log "Starting daemon process"
    Start-Process -FilePath "py" -ArgumentList $daemonArg -WorkingDirectory $projectRoot -WindowStyle Hidden
}

function Sync-DaemonStatusMirror {
    try {
        if (-not (Test-Path $daemonStatusLegacyPath)) {
            return
        }
        if (-not (Test-Path $daemonStatusV2Dir)) {
            New-Item -ItemType Directory -Path $daemonStatusV2Dir -Force | Out-Null
        }
        $copyRequired = -not (Test-Path $daemonStatusV2Path)
        if (-not $copyRequired) {
            $legacyTs = (Get-Item $daemonStatusLegacyPath).LastWriteTimeUtc
            $v2Ts = (Get-Item $daemonStatusV2Path).LastWriteTimeUtc
            $copyRequired = $legacyTs -gt $v2Ts
        }
        if ($copyRequired) {
            Copy-Item -Path $daemonStatusLegacyPath -Destination $daemonStatusV2Path -Force
            Write-Log "Synced daemon status mirror to v2/status"
        }
    } catch {
        Write-Log "WARN: Daemon status mirror sync failed: $($_.Exception.Message)"
    }
}

function Test-LockOwnerAlive {
    if (-not (Test-Path $lockPath)) {
        return $false
    }
    try {
        $raw = Get-Content $lockPath -Raw
        $obj = $raw | ConvertFrom-Json
        $ownerPid = [int]$obj.pid
        if ($ownerPid -gt 0) {
            return $null -ne (Get-Process -Id $ownerPid -ErrorAction SilentlyContinue)
        }
    } catch {
        Write-Log "Lock file parse failed: $($_.Exception.Message)"
    }
    return $false
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
        if (Test-LockOwnerAlive) {
            Write-Log "Daemon not listed by process query but heartbeat is fresh and lock owner alive - not starting another daemon."
            Sync-DaemonStatusMirror
            Write-Log "Daemon healthy"
            exit 0
        }
        Write-Log "Heartbeat is fresh but lock owner missing. Starting daemon to recover."
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
Sync-DaemonStatusMirror
