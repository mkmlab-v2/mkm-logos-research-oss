# Stop background PowerShell that runs infinite AIDC loop (AUTO_AIDC / while + run_aidc_bounded_loop).
$ErrorActionPreference = "Stop"
$hits = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
  $_.Name -match 'powershell|pwsh' -and $_.CommandLine -and (
    $_.CommandLine -match 'AUTO_AIDC_START' -or
    ($_.CommandLine -match 'run_aidc_bounded_loop' -and $_.CommandLine -match '\$true')
  )
}
foreach ($p in $hits) {
  Write-Host "Stopping PID=$($p.ProcessId)"
  Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Write-Host "Stopped $($hits.Count) process(es)."
