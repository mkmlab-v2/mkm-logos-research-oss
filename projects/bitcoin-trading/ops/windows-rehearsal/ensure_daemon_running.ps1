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

# Optional: install prometheus_client before daemon spawn (User env MKM_ENSURE_PROMETHEUS_CLIENT=1).
$ensureProm = [Environment]::GetEnvironmentVariable("MKM_ENSURE_PROMETHEUS_CLIENT", "Process")
if ([string]::IsNullOrWhiteSpace($ensureProm)) {
    $ensureProm = [Environment]::GetEnvironmentVariable("MKM_ENSURE_PROMETHEUS_CLIENT", "User")
}
if ($ensureProm -eq "1") {
    $reqProm = Join-Path $projectRoot "requirements-optional-prometheus.txt"
    if (Test-Path $reqProm) {
        try {
            py -m pip install -q -r $reqProm 2>&1 | Out-Null
        } catch {
            # non-fatal: daemon still runs without /metrics
        }
    }
}

# Optional: OpenTelemetry SDK (User env MKM_ENSURE_OTEL_CLIENT=1).
$ensureOtel = [Environment]::GetEnvironmentVariable("MKM_ENSURE_OTEL_CLIENT", "Process")
if ([string]::IsNullOrWhiteSpace($ensureOtel)) {
    $ensureOtel = [Environment]::GetEnvironmentVariable("MKM_ENSURE_OTEL_CLIENT", "User")
}
if ($ensureOtel -eq "1") {
    $reqOtel = Join-Path $projectRoot "requirements-optional-otel.txt"
    if (Test-Path $reqOtel) {
        try {
            py -m pip install -q -r $reqOtel 2>&1 | Out-Null
        } catch {
            # non-fatal: MKM_OTEL_ENABLED still no-ops without packages
        }
    }
}

if (-not (Test-Path $memoryDir)) {
    New-Item -ItemType Directory -Path $memoryDir | Out-Null
}

# Single-instance guard:
# prevent overlapping scheduled/manual runs from starting daemon twice.
$scriptLockPath = Join-Path $memoryDir "ensure_daemon_running.lock"
try {
    $script:WatchdogLockStream = [System.IO.File]::Open(
        $scriptLockPath,
        [System.IO.FileMode]::OpenOrCreate,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
} catch {
    Write-Host "[ensure-daemon] another watchdog instance is active; exiting."
    exit 0
}

function Write-Log([string]$message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
    Add-Content -Path $logPath -Value $line
    Write-Host $line
}

function Get-EnvAnyScope([string]$Name) {
    $p = [Environment]::GetEnvironmentVariable($Name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($p)) { return [string]$p }
    $u = [Environment]::GetEnvironmentVariable($Name, "User")
    if (-not [string]::IsNullOrWhiteSpace($u)) { return [string]$u }
    $m = [Environment]::GetEnvironmentVariable($Name, "Machine")
    if (-not [string]::IsNullOrWhiteSpace($m)) { return [string]$m }
    return ""
}

function Set-UserEnv([string]$Name, [string]$Value) {
    [Environment]::SetEnvironmentVariable($Name, $Value, "User")
    setx $Name $Value | Out-Null
}

function Get-DotenvValue([string]$path, [string]$key) {
    if (-not (Test-Path $path)) { return $null }
    try {
        foreach ($line in Get-Content -Path $path -Encoding UTF8) {
            if ($line -match '^\s*#') { continue }
            if ($line -match '^\s*$') { continue }
            $m = [regex]::Match($line, "^\s*{0}\s*=\s*(.*)\s*$" -f [regex]::Escape($key))
            if ($m.Success) {
                $v = $m.Groups[1].Value.Trim()
                if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
                    $v = $v.Substring(1, $v.Length - 2)
                }
                return $v
            }
        }
    } catch {
        return $null
    }
    return $null
}

function Get-DaemonStatusObject {
    $paths = @($daemonStatusV2Path, $daemonStatusLegacyPath)
    foreach ($p in $paths) {
        if (-not (Test-Path $p)) { continue }
        try {
            return (Get-Content $p -Raw | ConvertFrom-Json)
        } catch {
            continue
        }
    }
    return $null
}

function Test-ExchangeCredentialError([object]$statusObj) {
    if ($null -eq $statusObj) { return $false }
    try {
        $err = [string]$statusObj.exchange_snapshot_24h.error
        if ([string]::IsNullOrWhiteSpace($err)) { return $false }
        return $err -match "-2015"
    } catch {
        return $false
    }
}

function Get-CredentialErrorDiag([object]$statusObj) {
    if ($null -eq $statusObj) { return "status=missing" }
    try {
        $snap = $statusObj.exchange_snapshot_24h
        $err = [string]$snap.error
        $src = [string]$snap.credential_source
        $suffix = [string]$snap.credential_key_suffix
        if ([string]::IsNullOrWhiteSpace($src)) { $src = "unknown" }
        if ([string]::IsNullOrWhiteSpace($suffix)) { $suffix = "unknown" }
        if ([string]::IsNullOrWhiteSpace($err)) { $err = "none" }
        return ("source={0},key_suffix={1},error={2}" -f $src, $suffix, $err)
    } catch {
        return "status=parse_error"
    }
}

function Demote-ToHoldShadow {
    Write-Log "Demoting local mode to HOLD_SHADOW due to exchange credential error (-2015)."
    Set-UserEnv -Name "ALLOW_LIVE_TRADING_ON_LOCAL" -Value "0"
    Set-UserEnv -Name "LOCAL_DAEMON_HOLD_SHADOW" -Value "1"
    Set-UserEnv -Name "TESTNET" -Value "false"
    Set-UserEnv -Name "ENABLE_TRADING" -Value "false"
    # Ensure current watchdog process sees demotion immediately before restart.
    [Environment]::SetEnvironmentVariable("ALLOW_LIVE_TRADING_ON_LOCAL", "0", "Process")
    [Environment]::SetEnvironmentVariable("LOCAL_DAEMON_HOLD_SHADOW", "1", "Process")
    [Environment]::SetEnvironmentVariable("TESTNET", "false", "Process")
    [Environment]::SetEnvironmentVariable("ENABLE_TRADING", "false", "Process")
}

function Get-DaemonProcesses {
    # Do not filter Win32_Process.Name='python.exe' here: some shells report differently;
    # match by script path in CommandLine only.
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and
            ($_.CommandLine -match 'start_24h_daemon\.py') -and
            # Exclude launcher/wrapper shells to avoid false duplicate detection.
            # Actual daemon owner is the long-running python process.
            ($_.Name -notin @('py.exe', 'cmd.exe'))
        }
}

function Start-Daemon {
    if ($NoStart) {
        Write-Log "NoStart mode: start skipped"
        return
    }

    # Propagate risk-profile override flags to this process before sync.
    $riskAllowOverride = Get-EnvAnyScope -Name "RISK_PROFILE_ALLOW_CORE_HOLD_OVERRIDE"
    if (-not [string]::IsNullOrWhiteSpace($riskAllowOverride)) {
        [Environment]::SetEnvironmentVariable("RISK_PROFILE_ALLOW_CORE_HOLD_OVERRIDE", $riskAllowOverride, "Process")
    }
    $singularThreshold = Get-EnvAnyScope -Name "MKM_SINGULAR_CORE_THRESHOLD"
    if (-not [string]::IsNullOrWhiteSpace($singularThreshold)) {
        [Environment]::SetEnvironmentVariable("MKM_SINGULAR_CORE_THRESHOLD", $singularThreshold, "Process")
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

    # Stabilize Binance key source for watchdog restarts:
    # prefer workspace .env and inject into current process scope before daemon spawn.
    $envFile = "C:\workspace\.env"
    $apiKey = Get-DotenvValue -path $envFile -key "BINANCE_API_KEY"
    $apiSecret = Get-DotenvValue -path $envFile -key "BINANCE_API_SECRET"
    if (-not [string]::IsNullOrWhiteSpace($apiKey) -and -not [string]::IsNullOrWhiteSpace($apiSecret)) {
        [Environment]::SetEnvironmentVariable("BINANCE_API_KEY", $apiKey, "Process")
        [Environment]::SetEnvironmentVariable("BINANCE_API_SECRET", $apiSecret, "Process")
    } else {
        Write-Log "WARN: .env Binance credentials missing/empty; daemon will use fallback key source."
    }

    # Runtime guard env propagation: preserve execution behavior across watchdog restarts.
    $makerOnly = Get-EnvAnyScope -Name "MKM_MAKER_ONLY"
    if ([string]::IsNullOrWhiteSpace($makerOnly)) { $makerOnly = "1" }
    $minHoldSec = Get-EnvAnyScope -Name "POSITION_MIN_HOLD_SECONDS"
    if ([string]::IsNullOrWhiteSpace($minHoldSec)) { $minHoldSec = "600" }
    $reversalCooldownSec = Get-EnvAnyScope -Name "REVERSAL_COOLDOWN_SECONDS"
    if ([string]::IsNullOrWhiteSpace($reversalCooldownSec)) { $reversalCooldownSec = "600" }
    $strictMaker = Get-EnvAnyScope -Name "MKM_STRICT_MAKER_ENFORCEMENT"
    if ([string]::IsNullOrWhiteSpace($strictMaker)) { $strictMaker = "1" }
    $otelEnabled = Get-EnvAnyScope -Name "MKM_OTEL_ENABLED"
    if ([string]::IsNullOrWhiteSpace($otelEnabled)) { $otelEnabled = "0" }
    $otelConsole = Get-EnvAnyScope -Name "MKM_OTEL_CONSOLE"
    if ([string]::IsNullOrWhiteSpace($otelConsole)) { $otelConsole = "1" }
    $otlpTracesEndpoint = Get-EnvAnyScope -Name "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"
    $otlpEndpoint = Get-EnvAnyScope -Name "OTEL_EXPORTER_OTLP_ENDPOINT"
    $runtimeGuardPrefix = "set MKM_MAKER_ONLY=$makerOnly&& set POSITION_MIN_HOLD_SECONDS=$minHoldSec&& set REVERSAL_COOLDOWN_SECONDS=$reversalCooldownSec&& set MKM_STRICT_MAKER_ENFORCEMENT=$strictMaker&& set MKM_OTEL_ENABLED=$otelEnabled&& set MKM_OTEL_CONSOLE=$otelConsole&& "
    if (-not [string]::IsNullOrWhiteSpace($otlpTracesEndpoint)) {
        $runtimeGuardPrefix += "set OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=$otlpTracesEndpoint&& "
    }
    if (-not [string]::IsNullOrWhiteSpace($otlpEndpoint)) {
        $runtimeGuardPrefix += "set OTEL_EXPORTER_OTLP_ENDPOINT=$otlpEndpoint&& "
    }

    # Local default guardrail:
    # - Keep daemon in testnet + non-trading mode unless user explicitly allows live mode.
    # - This prevents accidental live orders after reboot/logon auto-recovery.
    # - hold_shadow: mainnet observation only (matches promotion gate hold_shadow recommendation).
    $allowLive = Get-EnvAnyScope -Name "ALLOW_LIVE_TRADING_ON_LOCAL"
    $holdShadow = Get-EnvAnyScope -Name "LOCAL_DAEMON_HOLD_SHADOW"
    if ($allowLive -eq "1") {
        Write-Log "Starting daemon process (LOCAL LIVE MODE ALLOWED)"
        $liveCommand = "${runtimeGuardPrefix}set TESTNET=false&& set ENABLE_TRADING=true&& py $daemonArg"
        Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $liveCommand) -WorkingDirectory $projectRoot -WindowStyle Hidden
        return
    }

    if ($holdShadow -eq "1") {
        Write-Log "Starting daemon process (HOLD_SHADOW: TESTNET=false, ENABLE_TRADING=false)"
        $holdShadowCommand = "${runtimeGuardPrefix}set TESTNET=false&& set ENABLE_TRADING=false&& py $daemonArg"
        Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $holdShadowCommand) -WorkingDirectory $projectRoot -WindowStyle Hidden
        return
    }

    $safeCommand = "${runtimeGuardPrefix}set TESTNET=true&& set ENABLE_TRADING=false&& py $daemonArg"
    Write-Log "Starting daemon process in SAFE MODE (TESTNET=true, ENABLE_TRADING=false)"
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $safeCommand) -WorkingDirectory $projectRoot -WindowStyle Hidden
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

function Update-RuntimeProbe([bool]$isRunning, [bool]$heartbeatStale, [bool]$lockOwnerAlive, [int]$daemonCount) {
    $statusPaths = @($daemonStatusLegacyPath, $daemonStatusV2Path)
    foreach ($statusPath in $statusPaths) {
        if (-not (Test-Path $statusPath)) {
            continue
        }
        try {
            $obj = Get-Content $statusPath -Raw | ConvertFrom-Json
            if ($null -eq $obj) { continue }
            $probe = [ordered]@{
                ts_utc = (Get-Date).ToUniversalTime().ToString("o")
                source = "ensure_daemon_running.ps1"
                daemon_process_count = $daemonCount
                daemon_process_running = $isRunning
                heartbeat_stale = $heartbeatStale
                lock_owner_alive = $lockOwnerAlive
            }
            $obj | Add-Member -NotePropertyName "runtime_probe" -NotePropertyValue $probe -Force
            $obj | ConvertTo-Json -Depth 12 | Set-Content -Path $statusPath -Encoding UTF8
        } catch {
            Write-Log "WARN: runtime_probe update failed for $statusPath : $($_.Exception.Message)"
        }
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
        $msg = $_.Exception.Message
        $isSharingViolation = $false
        # Locale-safe detection: lock read can fail with localized text on Windows.
        # Treat common IO lock/share violations as "owner alive" instead of parse failure.
        try {
            if ($_.Exception -is [System.IO.IOException]) {
                $isSharingViolation = $true
            } elseif ($_.Exception.InnerException -and ($_.Exception.InnerException -is [System.IO.IOException])) {
                $isSharingViolation = $true
            } elseif ($msg -match 'locked a portion of the file' -or $msg -match 'cannot access the file') {
                $isSharingViolation = $true
            }
        } catch {
            $isSharingViolation = $false
        }
        if ($isSharingViolation) {
            Write-Log "Lock file appears actively held by running daemon (sharing violation on read)."
            return $true
        }
        Write-Log "Lock file parse failed: $msg"
    }
    return $false
}

function Stop-DirectDaemonCopies {
    # bitcoin_trading_daemon.py bypasses start_24h_singleton.lock — remove strays each watchdog pass.
    $stopDirect = Join-Path $PSScriptRoot "stop_direct_bitcoin_trading_daemon_copies.ps1"
    if (-not (Test-Path $stopDirect)) {
        Write-Log "WARN: stop_direct_bitcoin_trading_daemon_copies.ps1 missing; skip direct-daemon cleanup"
        return
    }
    try {
        & $stopDirect
    } catch {
        Write-Log "WARN: Stop-DirectDaemonCopies failed: $($_.Exception.Message)"
    }
}

if (Test-Path $stopPath) {
    Write-Log "STOP.txt exists. Ensuring daemon is not running."
    $procs = Get-DaemonProcesses
    foreach ($p in $procs) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Log "Stopped daemon PID=$($p.ProcessId) due to kill switch"
    }
    Stop-DirectDaemonCopies
    Update-RuntimeProbe -isRunning $false -heartbeatStale $true -lockOwnerAlive $false -daemonCount 0
    exit 0
}

Stop-DirectDaemonCopies

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
$lockOwnerAlive = Test-LockOwnerAlive

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
        if ($lockOwnerAlive) {
            $allowLiveEarly = Get-EnvAnyScope -Name "ALLOW_LIVE_TRADING_ON_LOCAL"
            if ($allowLiveEarly -eq "1") {
                $statusEarly = Get-DaemonStatusObject
                if (Test-ExchangeCredentialError -statusObj $statusEarly) {
                    $diag = Get-CredentialErrorDiag -statusObj $statusEarly
                    Write-Log ("Detected -2015 while lock owner alive in live mode; forcing HOLD_SHADOW demotion + restart. [{0}]" -f $diag)
                    foreach ($p in $daemonProcs) {
                        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
                        Write-Log "Stopped live daemon PID=$($p.ProcessId) for safe demotion"
                    }
                    Demote-ToHoldShadow
                    Start-Daemon
                    Sync-DaemonStatusMirror
                    Update-RuntimeProbe -isRunning $false -heartbeatStale $heartbeatStale -lockOwnerAlive $lockOwnerAlive -daemonCount $daemonProcs.Count
                    exit 0
                }
            }
            Write-Log "Daemon not listed by process query but heartbeat is fresh and lock owner alive - not starting another daemon."
            Sync-DaemonStatusMirror
            Update-RuntimeProbe -isRunning $isRunning -heartbeatStale $heartbeatStale -lockOwnerAlive $lockOwnerAlive -daemonCount $daemonProcs.Count
            Write-Log "Daemon healthy"
            exit 0
        }
        Write-Log "Heartbeat is fresh but lock owner missing. Starting daemon to recover."
    }
    Write-Log "Daemon not running"
    Update-RuntimeProbe -isRunning $false -heartbeatStale $heartbeatStale -lockOwnerAlive $lockOwnerAlive -daemonCount $daemonProcs.Count
    Start-Daemon
    Sync-DaemonStatusMirror
    exit 0
}

if ($heartbeatStale) {
    Write-Log "Daemon running but heartbeat stale. Restarting."
    foreach ($p in $daemonProcs) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Log "Stopped stale daemon PID=$($p.ProcessId)"
    }
    Update-RuntimeProbe -isRunning $true -heartbeatStale $true -lockOwnerAlive $lockOwnerAlive -daemonCount $daemonProcs.Count
    Start-Daemon
    Sync-DaemonStatusMirror
    exit 0
}

# Safety fallback: if daemon is running in local live mode and exchange returns -2015,
# demote to HOLD_SHADOW and restart to avoid repeated live-mode churn with broken credentials.
$allowLiveNow = Get-EnvAnyScope -Name "ALLOW_LIVE_TRADING_ON_LOCAL"
if ($allowLiveNow -eq "1") {
    $statusObj = Get-DaemonStatusObject
    if (Test-ExchangeCredentialError -statusObj $statusObj) {
        $diag = Get-CredentialErrorDiag -statusObj $statusObj
        Write-Log ("Detected exchange_snapshot_24h credential error (-2015) while local live mode is enabled. [{0}]" -f $diag)
        foreach ($p in $daemonProcs) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Log "Stopped live daemon PID=$($p.ProcessId) for safe demotion"
        }
        Demote-ToHoldShadow
        Start-Daemon
        Sync-DaemonStatusMirror
        Update-RuntimeProbe -isRunning $true -heartbeatStale $heartbeatStale -lockOwnerAlive $lockOwnerAlive -daemonCount $daemonProcs.Count
        exit 0
    }
}

Write-Log "Daemon healthy"
Sync-DaemonStatusMirror
Update-RuntimeProbe -isRunning $isRunning -heartbeatStale $heartbeatStale -lockOwnerAlive $lockOwnerAlive -daemonCount $daemonProcs.Count
