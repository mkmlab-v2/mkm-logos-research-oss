param(
    [int]$Port = 8010,
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"

$workspace = "C:\workspace"
$stubScript = Join-Path $workspace "scripts\compression_token_api_stub.py"
$logPath = Join-Path $workspace "projects\bitcoin-trading\memory\watchdog_compression_stub.log"
$stdoutPath = Join-Path $workspace "projects\bitcoin-trading\memory\watchdog_compression_stub_stdout.log"
$stderrPath = Join-Path $workspace "projects\bitcoin-trading\memory\watchdog_compression_stub_stderr.log"

if (-not (Test-Path -LiteralPath (Split-Path -Parent $logPath))) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $logPath) -Force | Out-Null
}

function Write-Log([string]$message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
    Add-Content -Path $logPath -Value $line
    Write-Host $line
}

function Get-StubProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and
            ($_.CommandLine -match 'compression_token_api_stub\.py') -and
            ($_.Name -match '^(py|python|pythonw)(\.exe)?$')
        }
}

function Stop-StubProcesses {
    $procs = @(Get-StubProcesses)
    foreach ($p in $procs) {
        try {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Log ("Stopped stale compression stub PID={0}" -f $p.ProcessId)
        } catch {}
    }
}

function Test-StubHealth([int]$targetPort) {
    try {
        $resp = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/health" -f $targetPort) -Method Get -TimeoutSec 3
        return ($null -ne $resp -and [string]$resp.status -eq "ok")
    } catch {
        return $false
    }
}

function Wait-StubHealthy([int]$targetPort, [int]$retries = 10, [int]$sleepMs = 700) {
    for ($i = 0; $i -lt $retries; $i += 1) {
        if (Test-StubHealth -targetPort $targetPort) { return $true }
        Start-Sleep -Milliseconds $sleepMs
    }
    return $false
}

function Start-StubProcess([int]$targetPort) {
    $args = @("-m", "uvicorn", "scripts.compression_token_api_stub:app", "--host", "127.0.0.1", "--port", "$targetPort")
    if (Test-Path -LiteralPath "C:\WINDOWS\py.exe") {
        Start-Process -FilePath "C:\WINDOWS\py.exe" -ArgumentList $args -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath | Out-Null
    } else {
        Start-Process -FilePath "py" -ArgumentList $args -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath | Out-Null
    }
}

if (-not (Test-Path -LiteralPath $stubScript)) {
    throw "Compression stub script not found: $stubScript"
}

if (Wait-StubHealthy -targetPort $Port -retries 2) {
    Write-Log "Compression stub healthy (port=$Port)"
    exit 0
}

if ($NoStart) {
    Write-Log "NoStart enabled and compression stub not healthy (port=$Port)"
    exit 1
}

$existing = @(Get-StubProcesses)
if ($existing.Count -gt 0) {
    if (Wait-StubHealthy -targetPort $Port -retries 8) {
        Write-Log "Compression stub process already running and healthy (port=$Port)"
        exit 0
    }
    Write-Log "Compression stub process exists but unhealthy; recycling."
    Stop-StubProcesses
    Start-Sleep -Milliseconds 500
}

Write-Log "Starting compression stub (port=$Port)"
Start-StubProcess -targetPort $Port
if (-not (Wait-StubHealthy -targetPort $Port -retries 14)) {
    Write-Log "Compression stub failed to become healthy (port=$Port)"
    exit 1
}

Write-Log "Compression stub started and healthy (port=$Port)"
exit 0
