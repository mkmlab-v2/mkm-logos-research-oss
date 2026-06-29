# Stop ko shorts preview http.server on port (default 8796).
param(
    [int]$Port = 8796
)

$ErrorActionPreference = 'Stop'
$conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $conns) {
    Write-Host "OK: port $Port not listening"
    exit 0
}
$pids = $conns.OwningProcess | Sort-Object -Unique
foreach ($procId in $pids) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
    $cmd = $proc.CommandLine
    if ($cmd -match 'http\.server' -and $cmd -match "\s$Port(\s|$)") {
        Stop-Process -Id $procId -Force -ErrorAction Stop
        Write-Host "Stopped PID $procId (http.server $Port)"
    } else {
        Write-Host "SKIP PID $pid (not ko shorts preview http.server)" -ForegroundColor Yellow
    }
}
exit 0
