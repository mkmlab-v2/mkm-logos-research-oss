# Stop py.exe/python.exe running scripts/run_notebooklm_mega_insight_batch.py (long JSONL accumulation).
$ErrorActionPreference = "Stop"
$hits = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
  $_.CommandLine -and $_.CommandLine -match 'run_notebooklm_mega_insight_batch\.py'
}
foreach ($p in $hits) {
  Write-Host "Stopping PID=$($p.ProcessId) ($($p.Name))"
  Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Write-Host "Stopped $($hits.Count) process(es)."
