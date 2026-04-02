param(
    [string]$OverviewScriptPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\build_ops_health_overview.ps1",
    [string]$AppendScriptPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\append_ops_loop_snapshot.ps1",
    [string]$LoopMarkdownPath = "C:\workspace\docs\final\artifacts\OPS_NOTEBOOK_DRIVEN_LOOP_2026-04-02_2245.md"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $OverviewScriptPath)) {
    throw "Missing overview script: $OverviewScriptPath"
}
if (-not (Test-Path -LiteralPath $AppendScriptPath)) {
    throw "Missing append script: $AppendScriptPath"
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $OverviewScriptPath
if ($LASTEXITCODE -ne 0) {
    throw "Overview build failed. ExitCode=$LASTEXITCODE"
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $AppendScriptPath -TargetMarkdownPath $LoopMarkdownPath
if ($LASTEXITCODE -ne 0) {
    throw "Append snapshot failed. ExitCode=$LASTEXITCODE"
}

Write-Host "OK overview build + loop snapshot append completed"
