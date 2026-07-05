# Build-KmHanMedicineUiUxHandoffZip_v1.ps1
# Assembles projects/km_han_medicine_ui_ux bundle + reports/km_han_medicine_ui_ux_v1.zip
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$OutZip = ""
)

$ErrorActionPreference = "Stop"
$PackRoot = Join-Path $RepoRoot "projects\km_han_medicine_ui_ux"
$Staging = Join-Path $env:TEMP "km_han_medicine_ui_ux_staging_$(Get-Date -Format 'yyyyMMddHHmmss')"

if (-not $OutZip) {
    $OutZip = Join-Path $RepoRoot "reports\km_han_medicine_ui_ux_v1.zip"
}

$copyMap = @(
    @{ Src = "reports\km_han_medicine_antigravity_ui_ux_prompt_v1.md"; Dst = "prompts\km_han_medicine_antigravity_ui_ux_prompt_v1.md" },
    @{ Src = "reports\paste_chart_antigravity_prompt_v2_surface.md"; Dst = "prompts\paste_chart_antigravity_prompt_v2_surface.md" },
    @{ Src = "reports\km_han_medicine_antigravity_ui_ux_handoff_v1.md"; Dst = "handoff\km_han_medicine_antigravity_ui_ux_handoff_v1.md" },
    @{ Src = "docs\final\artifacts\jemaai_antigravity_design_prompt_packs_v1_latest.md"; Dst = "ssot\jemaai_antigravity_design_prompt_packs_v1_latest.md" },
    @{ Src = "docs\final\artifacts\jemaai_dtcg_tokens_proposed_v1.dtcg.json"; Dst = "ssot\jemaai_dtcg_tokens_proposed_v1.dtcg.json" },
    @{ Src = "docs\final\artifacts\jemaai_design_reference_seed_antigravity_v1.json"; Dst = "ssot\jemaai_design_reference_seed_antigravity_v1.json" },
    @{ Src = "docs\final\artifacts\mkm_ai_han_medicine_concept_stack_v1_latest.json"; Dst = "ssot\mkm_ai_han_medicine_concept_stack_v1_latest.json" }
)

$staticDirs = @(
    "README.md",
    "SETUP.md",
    "cursor\MERGE_CHECKLIST.md",
    "mocks\README.md"
)

Write-Host "[km-handoff] staging -> $Staging"
New-Item -ItemType Directory -Force -Path $Staging | Out-Null

foreach ($rel in $staticDirs) {
    $src = Join-Path $PackRoot $rel
    $dst = Join-Path $Staging $rel
    if (-not (Test-Path $src)) {
        throw "Missing static file: $src"
    }
    $parent = Split-Path $dst -Parent
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    Copy-Item -LiteralPath $src -Destination $dst -Force
}

foreach ($item in $copyMap) {
    $src = Join-Path $RepoRoot $item.Src
    $dst = Join-Path $Staging $item.Dst
    if (-not (Test-Path $src)) {
        throw "Missing SSOT: $src"
    }
    $parent = Split-Path $dst -Parent
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    Copy-Item -LiteralPath $src -Destination $dst -Force
    Write-Host "  copied $($item.Src)"
}

# Copy existing mocks if any (exclude build junk)
$mockSrc = Join-Path $PackRoot "mocks"
$mockDst = Join-Path $Staging "mocks"
if (Test-Path $mockSrc) {
    Get-ChildItem -LiteralPath $mockSrc -Force | Where-Object {
        $_.Name -notin @("README.md", "build", ".gradle", ".idea")
    } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $mockDst -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$manifest = @{
    schema = "km_han_medicine_ui_ux_handoff_manifest_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    files = @()
}
Get-ChildItem -LiteralPath $Staging -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($Staging.Length).TrimStart("\")
    $manifest.files += $rel
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $Staging "MANIFEST.json") -Encoding UTF8

$zipDir = Split-Path $OutZip -Parent
if (-not (Test-Path $zipDir)) {
    New-Item -ItemType Directory -Force -Path $zipDir | Out-Null
}
if (Test-Path $OutZip) {
    Remove-Item -LiteralPath $OutZip -Force
}

Write-Host "[km-handoff] zip -> $OutZip"
$zipItems = Get-ChildItem -LiteralPath $Staging -Force
Compress-Archive -Path ($zipItems | ForEach-Object { $_.FullName }) -DestinationPath $OutZip -CompressionLevel Optimal -Force

Remove-Item -LiteralPath $Staging -Recurse -Force

Write-Host "[km-handoff] ok files=$($manifest.files.Count) zip=$OutZip"
exit 0
