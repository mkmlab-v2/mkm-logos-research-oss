param(
    [string]$Approver = "manual_operator",
    [string]$Note = "Manual approval for A-track reflection packet generation (no live auto bridge).",
    [switch]$SkipConstitutionGate
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "[1/4] Apply human approval (reapprove allowed for idempotent ops)..."
py "scripts/promote_logos_symbolic_with_human_approval_v1.py" `
    --approver $Approver `
    --note $Note `
    --allow-reapprove

if (-not $SkipConstitutionGate) {
    Write-Host "[2/4] Verify constitution gate paths..."
    powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/verify_p0_constitution_gate_paths.ps1"
}
else {
    Write-Host "[2/4] Skip constitution gate verification (requested)."
}

Write-Host "[3/4] Rebuild final GO/NO-GO signoff packet..."
py "scripts/build_logos_symbolic_release_signoff_packet_v1.py"

Write-Host "[4/4] Print concise final decision..."
$packetPath = "docs/final/artifacts/logos_symbolic_release_signoff_packet_latest.json"
$packet = Get-Content -Path $packetPath -Raw | ConvertFrom-Json
Write-Host ("recommended_manual_gate=" + [string]$packet.summary.recommended_manual_gate)
Write-Host ("all_checks_pass=" + [string]$packet.summary.all_checks_pass)

Write-Host "DONE: logos symbolic release signoff chain completed."

