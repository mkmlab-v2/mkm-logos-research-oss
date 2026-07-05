# Prepare-KmHanMedicineBundle_v1.ps1
# Syncs repo SSOT into projects/km_han_medicine_ui_ux for Antigravity mock drop + Cursor handoff.
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$BuildZip
)

$ErrorActionPreference = "Stop"
$BundleRoot = Join-Path $RepoRoot "projects\km_han_medicine_ui_ux"

$copyMap = @(
    @{ Src = "reports\km_han_medicine_antigravity_ui_ux_prompt_v1.md"; Dst = "prompts\km_han_medicine_antigravity_ui_ux_prompt_v1.md" },
    @{ Src = "reports\paste_chart_antigravity_prompt_v2_surface.md"; Dst = "prompts\paste_chart_antigravity_prompt_v2_surface.md" },
    @{ Src = "reports\km_han_medicine_antigravity_ui_ux_handoff_v1.md"; Dst = "handoff\km_han_medicine_antigravity_ui_ux_handoff_v1.md" },
    @{ Src = "docs\final\artifacts\jemaai_antigravity_design_prompt_packs_v1_latest.md"; Dst = "ssot\jemaai_antigravity_design_prompt_packs_v1_latest.md" },
    @{ Src = "docs\final\artifacts\jemaai_dtcg_tokens_proposed_v1.dtcg.json"; Dst = "ssot\jemaai_dtcg_tokens_proposed_v1.dtcg.json" },
    @{ Src = "docs\final\artifacts\jemaai_design_reference_seed_antigravity_v1.json"; Dst = "ssot\jemaai_design_reference_seed_antigravity_v1.json" },
    @{ Src = "docs\final\artifacts\mkm_ai_han_medicine_concept_stack_v1_latest.json"; Dst = "ssot\mkm_ai_han_medicine_concept_stack_v1_latest.json" }
)

$dirs = @(
    "prompts",
    "ssot",
    "handoff",
    "cursor",
    "mocks\PackE-NationalAsk",
    "mocks\PackF-Clinician",
    "mocks\PackG-HubClinical"
)

Write-Host "[km-prepare] bundle -> $BundleRoot"
New-Item -ItemType Directory -Force -Path $BundleRoot | Out-Null
foreach ($rel in $dirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $BundleRoot $rel) | Out-Null
}

foreach ($item in $copyMap) {
    $src = Join-Path $RepoRoot $item.Src
    $dst = Join-Path $BundleRoot $item.Dst
    if (-not (Test-Path $src)) {
        throw "Missing SSOT: $src (use docs/final/artifacts/ — not c:\workspace\artifacts\)"
    }
    Copy-Item -LiteralPath $src -Destination $dst -Force
    Write-Host "  copied $($item.Src)"
}

$manifestPath = Join-Path $BundleRoot "manifest.txt"
$manifestBody = @"
KM Han Medicine UI/UX - Antigravity pack order
generated: $((Get-Date).ToUniversalTime().ToString("o"))

1. Pack A supplement (.km-ask-* -> DTCG trust.clinical)
2. Pack E - no1kmedi.com/ask (L0 national KM)
3. Pack F - clinic.no1kmedi.com/clinician (Paste Chart + cite spine)
4. Pack G - jema-ai.com/hub clinical group

Mock drop zones:
  mocks/PackE-NationalAsk/
  mocks/PackF-Clinician/
  mocks/PackG-HubClinical/

SSOT: projects/km_han_medicine_ui_ux/ssot/
Prompt: projects/km_han_medicine_ui_ux/prompts/km_han_medicine_antigravity_ui_ux_prompt_v1.md
"@
[System.IO.File]::WriteAllText($manifestPath, $manifestBody, [System.Text.UTF8Encoding]::new($true))

$fileCount = (Get-ChildItem -LiteralPath $BundleRoot -Recurse -File).Count
Write-Host "[km-prepare] ok files=$fileCount root=$BundleRoot"

if ($BuildZip) {
    $buildScript = Join-Path $RepoRoot "scripts\Build-KmHanMedicineUiUxHandoffZip_v1.ps1"
    & $buildScript -RepoRoot $RepoRoot
}

exit 0
