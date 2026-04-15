param(
    [int]$Port = 8788,
    [switch]$NoStart,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$mutexName = "Global\MKM12_PublicEventGateway_Ensure_Lock"
$mutex = New-Object System.Threading.Mutex($false, $mutexName)
$lockTaken = $false

$workspace = "C:\workspace"
$gatewayScript = Join-Path $workspace "projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp\public_event_gateway.py"
$logPath = Join-Path $workspace "projects\bitcoin-trading\memory\watchdog_public_event_gateway.log"
$pythonStdoutLogPath = Join-Path $workspace "projects\bitcoin-trading\memory\watchdog_public_event_gateway_stdout.log"
$pythonStderrLogPath = Join-Path $workspace "projects\bitcoin-trading\memory\watchdog_public_event_gateway_stderr.log"

if (-not (Test-Path -LiteralPath (Split-Path -Parent $logPath))) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $logPath) -Force | Out-Null
}

function Write-Log([string]$message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
    Add-Content -Path $logPath -Value $line
    Write-Host $line
}

function Start-GatewayProcess {
    if ($Port -ne 8788) {
        $env:PUBLIC_EVENT_GATEWAY_PORT = [string]$Port
    }
    if (Test-Path -LiteralPath "C:\WINDOWS\py.exe") {
        Start-Process -FilePath "C:\WINDOWS\py.exe" -ArgumentList @("-u", $gatewayScript) -WindowStyle Hidden -RedirectStandardOutput $pythonStdoutLogPath -RedirectStandardError $pythonStderrLogPath | Out-Null
    } else {
        Start-Process -FilePath "py" -ArgumentList @("-u", $gatewayScript) -WindowStyle Hidden -RedirectStandardOutput $pythonStdoutLogPath -RedirectStandardError $pythonStderrLogPath | Out-Null
    }
}

function Get-FileTailText([string]$Path, [int]$TailLines = 30) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return ""
    }
    try {
        $lines = Get-Content -LiteralPath $Path -Tail $TailLines -ErrorAction Stop
        if ($null -eq $lines) {
            return ""
        }
        return ($lines -join "`n")
    } catch {
        return ""
    }
}

function Test-GatewayHttp([int]$targetPort) {
    try {
        $url = "http://127.0.0.1:{0}/api/public-events/latest" -f $targetPort
        $req = [System.Net.HttpWebRequest]::Create($url)
        $req.Method = "GET"
        $req.Timeout = 5000
        $req.ReadWriteTimeout = 5000
        $req.Proxy = $null
        $resp = $req.GetResponse()
        $statusCode = [int]$resp.StatusCode
        $resp.Close()
        return ($statusCode -ge 200 -and $statusCode -lt 400)
    } catch {
        return $false
    }
}

function Get-GatewayProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and
            ($_.CommandLine -match 'public_event_gateway\.py') -and
            ($_.Name -match '^(py|python|pythonw)(\.exe)?$')
        }
}

function Stop-GatewayProcesses {
    $procs = @(Get-GatewayProcesses)
    foreach ($p in $procs) {
        try {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Log ("Stopped stale gateway PID={0}" -f $p.ProcessId)
        } catch {
            # ignore
        }
    }
}

function Stop-PortOwnerIfGateway([int]$targetPort) {
    try {
        $listeners = @(Get-NetTCPConnection -LocalPort $targetPort -State Listen -ErrorAction SilentlyContinue)
    } catch {
        $listeners = @()
    }
    if ($listeners.Count -eq 0) {
        return $false
    }
    foreach ($row in $listeners) {
        $pid = [int]$row.OwningProcess
        try {
            $proc = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $pid)
        } catch {
            $proc = $null
        }
        if ($proc -and $proc.CommandLine -and $proc.CommandLine -match 'public_event_gateway\.py') {
            try {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Log ("Killed stale gateway port owner PID={0} on port {1}" -f $pid, $targetPort)
                return $true
            } catch {
                # ignore
            }
        }
    }
    return $false
}

function Test-GatewayPortListening([int]$targetPort) {
    try {
        $listeners = Get-NetTCPConnection -LocalPort $targetPort -State Listen -ErrorAction SilentlyContinue
        return ($null -ne $listeners -and $listeners.Count -ge 1)
    } catch {
        return $false
    }
}

function Wait-GatewayHealthy([int]$targetPort, [int]$retries = 6, [int]$sleepSeconds = 1) {
    for ($i = 0; $i -lt $retries; $i++) {
        if ((Test-GatewayPortListening $targetPort) -or (Test-GatewayHttp $targetPort)) {
            return $true
        }
        Start-Sleep -Seconds $sleepSeconds
    }
    return $false
}

try {
    if (-not $mutex.WaitOne(15000)) {
        Write-Log "Gateway ensure lock timeout; another ensure instance is active."
        if (Wait-GatewayHealthy -targetPort $Port -retries 12 -sleepSeconds 1) {
            Write-Log "Gateway healthy while waiting on lock; treating ensure as successful."
            exit 0
        }
        if ($Strict) {
            Write-Log "STRICT mode: lock contention and gateway did not become healthy in time."
            exit 1
        }
        exit 0
    }
    $lockTaken = $true

    if (-not (Test-Path -LiteralPath $gatewayScript)) {
        throw "Gateway script not found: $gatewayScript"
    }

    if (Wait-GatewayHealthy -targetPort $Port -retries 2 -sleepSeconds 1) {
        Write-Log "Public Event Gateway healthy (port=$Port)"
        exit 0
    }

    $gatewayProcs = @(Get-GatewayProcesses)
    if ($gatewayProcs.Count -gt 0) {
        if (Wait-GatewayHealthy -targetPort $Port -retries 5 -sleepSeconds 1) {
            Write-Log "Gateway process already running and healthy (port=$Port)"
            exit 0
        }
        if (Wait-GatewayHealthy -targetPort $Port -retries 10 -sleepSeconds 1) {
            Write-Log "Gateway process became healthy after warmup (port=$Port)"
            exit 0
        }
        if ($gatewayProcs.Count -ge 4) {
            Write-Log "Too many gateway processes detected; recycling duplicates."
            Stop-GatewayProcesses
            Start-Sleep -Seconds 1
        } else {
            Write-Log "Gateway process exists but probe still unstable; avoiding duplicate start."
            if (Wait-GatewayHealthy -targetPort $Port -retries 20 -sleepSeconds 1) {
                Write-Log "Gateway process eventually healthy after extended wait (port=$Port)"
                exit 0
            }
            if ($Strict) {
                Write-Log "STRICT mode: existing process did not pass warmup health checks."
                exit 1
            }
            exit 0
        }
    }

    if ($NoStart) {
        Write-Log "NoStart enabled and gateway not healthy (port=$Port)"
        exit 1
    }

    Write-Log "Gateway not healthy -> starting process (port=$Port)"
    Start-GatewayProcess
    if (-not (Wait-GatewayHealthy -targetPort $Port -retries 8 -sleepSeconds 1)) {
        Write-Log "Gateway start attempted but health check failed (port=$Port). Retrying once."
        Stop-GatewayProcesses
        Start-Sleep -Seconds 1
        Start-GatewayProcess
    }
    if (-not (Wait-GatewayHealthy -targetPort $Port -retries 10 -sleepSeconds 1)) {
        $killedPortOwner = Stop-PortOwnerIfGateway -targetPort $Port
        if ($killedPortOwner) {
            Write-Log "Retrying gateway bootstrap after conditional port-owner cleanup."
            Start-Sleep -Seconds 1
            Start-GatewayProcess
            if (Wait-GatewayHealthy -targetPort $Port -retries 8 -sleepSeconds 1) {
                Write-Log "Gateway healthy after conditional port-owner cleanup (port=$Port)"
                exit 0
            }
        }
        $postRetryProcs = @(Get-GatewayProcesses)
        if ($postRetryProcs.Count -gt 0 -and -not $Strict) {
            Write-Log "Gateway health probe failed but process exists; proceeding in degraded mode."
            exit 0
        }
        $stderrTail = Get-FileTailText -Path $pythonStderrLogPath -TailLines 30
        if ($stderrTail) {
            Write-Log ("Gateway stderr tail (recent):`n{0}" -f $stderrTail)
        }
        if ($Strict) {
            Write-Log "Gateway restart retry failed in STRICT mode (port=$Port)"
        } else {
            Write-Log "Gateway restart retry failed (port=$Port)"
        }
        exit 1
    }

    Write-Log "Gateway started and healthy (port=$Port)"
    exit 0
}
finally {
    if ($lockTaken) {
        $mutex.ReleaseMutex() | Out-Null
    }
    $mutex.Dispose()
}
