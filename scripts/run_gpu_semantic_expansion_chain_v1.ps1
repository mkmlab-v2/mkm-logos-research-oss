param(
    [switch]$SkipConstitutionGate
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "[1/3] Build GPU semantic expansion backlog artifact..."
py "scripts/build_gpu_semantic_expansion_backlog_v1.py"

if (-not $SkipConstitutionGate) {
    Write-Host "[2/3] Verify constitution gate paths..."
    powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/verify_p0_constitution_gate_paths.ps1"
} else {
    Write-Host "[2/3] Skip constitution gate verification (requested)."
}

Write-Host "[3/3] Refresh release-ready index snapshot..."
py "scripts/build_track_a_release_ready_index_v1.py"

Write-Host "DONE: GPU semantic expansion chain prepared (research-only backlog)."
