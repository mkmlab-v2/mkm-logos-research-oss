param(
    [int]$RunsPerPrompt = 10,
    [switch]$StrictCoverageGate
)

$ErrorActionPreference = "Stop"
$scripts = Split-Path -Parent $MyInvocation.MyCommand.Path

$chain = Join-Path $scripts "run_vibe_shadow_loop_chain_v1.ps1"
$evo = Join-Path $scripts "build_vibe_evolution_suggestions_v1.py"
$validateExternal = Join-Path $scripts "validate_vibe_external_inputs_v1.py"
$pendingPackets = Join-Path $scripts "build_athena_pending_request_packets_v1.py"
$pendingBatches = Join-Path $scripts "build_athena_pending_batches_v1.py"
$bootstrapQueue = Join-Path $scripts "build_vibe_bootstrap_replacement_queue_v1.py"
$dashboard = Join-Path $scripts "build_vibe_daily_status_dashboard_v1.py"

Write-Host "[daily-loop] start" -ForegroundColor Cyan
Write-Host "[daily-loop] step=prophecy_shadow_chain"
if ($StrictCoverageGate) {
    powershell -NoProfile -ExecutionPolicy Bypass -File $chain -RunsPerPrompt $RunsPerPrompt -StrictCoverageGate
} else {
    powershell -NoProfile -ExecutionPolicy Bypass -File $chain -RunsPerPrompt $RunsPerPrompt
}
if ($LASTEXITCODE -ne 0) {
    throw "[daily-loop] prophecy_shadow_chain failed (exit=$LASTEXITCODE)"
}

Write-Host "[daily-loop] step=evolution_suggestions"
py $evo

Write-Host "[daily-loop] step=validate_external_inputs"
py $validateExternal
if ($LASTEXITCODE -ne 0) {
    throw "[daily-loop] external input validation failed (exit=$LASTEXITCODE)"
}

Write-Host "[daily-loop] step=build_pending_request_packets"
py $pendingPackets

Write-Host "[daily-loop] step=build_pending_batches"
py $pendingBatches

Write-Host "[daily-loop] step=daily_status_dashboard"
py $dashboard

Write-Host "[daily-loop] step=bootstrap_replacement_queue"
py $bootstrapQueue

Write-Host "[daily-loop] done (suggestions created, no auto-apply)" -ForegroundColor Green
