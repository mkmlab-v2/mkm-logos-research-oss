# Weekly ops: B-track intake chain → deploy showroom staging → optional VPS sync → optional public smoke.
param(
    [string]$IntakeJson = "tests/fixtures/patient_intake_soeum_clinical_v1.example.json",
    [switch]$ApplyIjeomaHarvest,
    [switch]$PruneIjeomaHarvestLexicon,
    [switch]$SkipTrackCDashboard,
    [switch]$SkipShowroomTrustSlice,
    [switch]$SkipMirrorStaging,
    [switch]$SkipDeployShowroom,
    [switch]$SkipSyncToVps,
    [switch]$SkipPublicSmoke,
    [switch]$BuildAllConstitutions,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$chain = Join-Path $PSScriptRoot "Run-PatientIntakeFusionBtrackChain_v1.ps1"
$deploy = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\deploy_showroom_static.ps1"
$sync = Join-Path $PSScriptRoot "sync_showroom_to_vps.ps1"

$chainArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $chain, "-IntakeJson", $IntakeJson)
if (-not $SkipTrackCDashboard) { $chainArgs += "-IncludeTrackCDashboard" }
if (-not $SkipShowroomTrustSlice) { $chainArgs += "-IncludeShowroomTrustSlice" }
if (-not $SkipMirrorStaging) { $chainArgs += "-MirrorShowroomStaging" }
if ($ApplyIjeomaHarvest) { $chainArgs += "-ApplyIjeomaHarvest" }
if ($PruneIjeomaHarvestLexicon) { $chainArgs += "-PruneIjeomaHarvestLexicon" }

if ($BuildAllConstitutions) {
    py scripts/build_patient_intake_fusion_all_constitutions_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($DryRun) {
    Write-Host "[patient-intake-weekly] DRY_RUN chain: $($chainArgs -join ' ')"
    if ($BuildAllConstitutions) { Write-Host "[patient-intake-weekly] DRY_RUN four-constitution smoke" }
    if (-not $SkipDeployShowroom) { Write-Host "[patient-intake-weekly] DRY_RUN deploy: $deploy" }
    if (-not $SkipSyncToVps) { Write-Host "[patient-intake-weekly] DRY_RUN sync: $sync" }
    if (-not $SkipPublicSmoke) { Write-Host "[patient-intake-weekly] DRY_RUN smoke: py scripts/check_showroom_trust_viz_public_chain_v1.py" }
    exit 0
}

& powershell.exe @chainArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipDeployShowroom) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $deploy -WorkspaceRoot $root
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipSyncToVps) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $sync
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipPublicSmoke) {
    py scripts/check_showroom_trust_viz_public_chain_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[patient-intake-weekly] OK" -ForegroundColor Green
exit 0
