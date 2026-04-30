param(
    [string]$Reviewer = "PRO",
    [string]$Note = "Prophecy release sign-off chain executed.",
    [switch]$SkipConstitutionGate
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "[1/5] Refresh prophecy release signoff packet..."
py "scripts/build_prophecy_release_signoff_packet_v1.py"

if (-not $SkipConstitutionGate) {
    Write-Host "[2/5] Verify constitution gate paths..."
    powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/verify_p0_constitution_gate_paths.ps1"
} else {
    Write-Host "[2/5] Skip constitution gate verification (requested)."
}

Write-Host "[3/5] Record human release signoff event..."
py "scripts/record_prophecy_release_human_signoff_v1.py" --reviewer $Reviewer --decision APPROVED --note $Note

Write-Host "[4/5] Refresh approved-candidate release checklist..."
py "scripts/build_prophecy_approved_candidate_release_checklist_v1.py"

Write-Host "[5/5] Refresh release-ready index..."
py "scripts/build_track_a_release_ready_index_v1.py"

Write-Host "DONE: prophecy release signoff chain completed."
