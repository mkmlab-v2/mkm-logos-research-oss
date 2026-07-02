# Stop stray Next dev listeners on Logos research ports (3010-3035 band).
param(
    [int[]]$Ports = @(3010, 3011, 3012, 3035),
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$stopped = @()

foreach ($port in $Ports) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $conns) {
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        if (-not $proc) { continue }
        $name = $proc.ProcessName
        if ($WhatIf) {
            Write-Host "would stop PID $($proc.Id) ($name) on :$port"
            continue
        }
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        $stopped += @{ port = $port; pid = $proc.Id; name = $name }
        Write-Host "stopped PID $($proc.Id) ($name) on :$port"
    }
}

if ($WhatIf) {
    Write-Host "WhatIf only — no processes stopped"
    exit 0
}

Write-Host "OK stopped=$($stopped.Count)"
