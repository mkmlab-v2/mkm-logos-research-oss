param(
    [string]$Approver = "PRO",
    [string]$Note = "Commander approved for manual A-track gate review submission.",
    [switch]$SkipConstitutionGate
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "[1/10] Run release signoff chain..."
$releaseChainArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/run_logos_symbolic_release_signoff_chain_v1.ps1",
    "-Approver", $Approver,
    "-Note", $Note
)
if ($SkipConstitutionGate) {
    $releaseChainArgs += "-SkipConstitutionGate"
}
powershell @releaseChainArgs

Write-Host "[2/10] Build A-track review onepager..."
py "scripts/build_logos_symbolic_a_track_review_onepager_v1.py"

Write-Host "[3/10] Build paid-user brief (baseline)..."
py "scripts/build_logos_symbolic_paid_user_brief_v1.py"

Write-Host "[4/10] Run paid-user brief stress test..."
py "scripts/run_logos_symbolic_paid_brief_stress_test_v1.py"

Write-Host "[5/10] Rebuild paid-user brief (with stress summary)..."
py "scripts/build_logos_symbolic_paid_user_brief_v1.py"

Write-Host "[6/10] Build showroom public-event bundle..."
py "scripts/build_logos_showroom_public_bundle_from_paid_brief_v1.py"
py "scripts/validate_showroom_public_bundle.py" "c:/workspace/docs/final/artifacts/logos_showroom_public_bundle_latest.json"

Write-Host "[7/10] Build review submission bundle..."
py "scripts/build_logos_symbolic_review_submission_bundle_v1.py"

Write-Host "[8/10] Print packet decision..."
$packetPath = "docs/final/artifacts/logos_symbolic_release_signoff_packet_latest.json"
$packet = Get-Content -Path $packetPath -Raw | ConvertFrom-Json
Write-Host ("recommended_manual_gate=" + [string]$packet.summary.recommended_manual_gate)
Write-Host ("all_checks_pass=" + [string]$packet.summary.all_checks_pass)

Write-Host "[9/10] Print bundle outputs..."
$manifestPath = "docs/final/artifacts/logos_symbolic_review_submission_bundle_manifest_latest.json"
$manifest = Get-Content -Path $manifestPath -Raw | ConvertFrom-Json
Write-Host ("bundle_zip=" + [string]$manifest.bundle_zip)
Write-Host ("bundle_sha256=" + [string]$manifest.bundle_sha256)
Write-Host ("bundle_file_count=" + [string]$manifest.file_count)

Write-Host "[10/10] Run showroom consumer path smoke..."
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run_logos_showroom_consumer_path_smoke_v1.ps1" -WorkspaceRoot $repoRoot -SyncAsDefaultBundle
if ($LASTEXITCODE -ne 0) {
    throw "showroom consumer path smoke failed"
}

Write-Host "DONE: logos symbolic submission pack completed."

