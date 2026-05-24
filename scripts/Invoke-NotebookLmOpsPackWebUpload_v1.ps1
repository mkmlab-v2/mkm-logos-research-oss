# Open 00_OPS notebook + ops sync pack folder for drag-and-drop upload (fastest when MCP Chrome conflicts).
param(
    [string]$NotebookUrl = "https://notebooklm.google.com/notebook/9bc26140-70c4-47d0-b9ea-bd3a394916a9",
    [string]$PackDir = "$PSScriptRoot\..\reports\notebooklm_ops_command_sync_pack_v1"
)
$PackDir = (Resolve-Path $PackDir).Path
Write-Host "Pack: $PackDir (9 files — drag all into NL Sources)"
Write-Host "Notebook: $NotebookUrl"
Start-Process explorer.exe $PackDir
Start-Process $NotebookUrl
