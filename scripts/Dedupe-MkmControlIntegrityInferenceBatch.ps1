# Dedupe run_mkm_control_integrity_inference_batch_v1.py: keep newest, stop older duplicates.
$ErrorActionPreference = 'Stop'
$matches = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*run_mkm_control_integrity_inference_batch_v1*' }

if (-not $matches) {
    Write-Host 'No matching inference_batch processes found.'
    exit 0
}

$rows = foreach ($m in @($matches)) {
    [PSCustomObject]@{
        PID     = $m.ProcessId
        Started = $m.CreationDate
        Cmd     = $m.CommandLine
    }
}

$sorted = $rows | Sort-Object Started
Write-Host '=== Inference batch processes (oldest first) ==='
$sorted | Format-Table PID, Started -AutoSize

if ($sorted.Count -le 1) {
    Write-Host 'Only one process; nothing to stop.'
    exit 0
}

$keep = $sorted | Select-Object -Last 1
$kill = $sorted | Select-Object -SkipLast 1

Write-Host "KEEP (newest): PID $($keep.PID) started $($keep.Started)"
foreach ($k in $kill) {
    Write-Host "STOP duplicate: PID $($k.PID) started $($k.Started)"
    Stop-Process -Id $k.PID -Force -ErrorAction Continue
}

Write-Host 'Done.'
