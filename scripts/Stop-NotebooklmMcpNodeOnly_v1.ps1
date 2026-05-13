<#
.SYNOPSIS
  Kill ONLY node.exe processes whose command line references notebooklm-mcp.

.NOTES
  After this, Cursor shows NotebookLM MCP as "Not connected" until
  Developer: Reload Window (or MCP notebooklm toggle OFF/ON).
  Prefer Reload Window alone after editing global notebooklm-mcp files;
  use this script only when you intentionally force MCP to restart.
#>
# Kill only node.exe processes whose command line references notebooklm-mcp.
$ErrorActionPreference = "Stop"
$procs = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "node.exe" -and $_.CommandLine -match "notebooklm-mcp"
})
if ($procs.Count -eq 0) {
    Write-Host "No notebooklm-mcp node process found."
    exit 0
}
foreach ($x in $procs) {
    Write-Host ("Stopping PID {0}" -f $x.ProcessId)
    Stop-Process -Id $x.ProcessId -Force -ErrorAction SilentlyContinue
}
Write-Host "Done."
exit 0
