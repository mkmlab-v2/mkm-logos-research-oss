<#
.SYNOPSIS
  Mirrors NotebookLM source paths (SSOT: docs/NotebookLM_sources_manifest.md) into the shared MKM vault.

.DESCRIPTION
  Copies listed files and one directory tree from the workspace to:
    G:\공유 드라이브\MKM_DATA_VAULT\vault\notebooklm_sources\<relative path>
  Missing optional sources are skipped with a warning unless -Strict.

.NOTES
  When adding/removing sources, update docs/NotebookLM_sources_manifest.md and the $SourceFiles / $SourceDirs arrays below.

.PARAMETER WorkspaceRoot
  Repository root (default: parent of scripts/).

.PARAMETER VaultRoot
  Target vault folder (default: G:\공유 드라이브\MKM_DATA_VAULT\vault).

.PARAMETER MirrorSubfolder
  Subfolder under VaultRoot for the mirror (default: notebooklm_sources).

.PARAMETER WhatIf
  Print planned copies only; do not write.

.PARAMETER Strict
  Fail if any listed source path is missing.

  If -VaultRoot is omitted and the default path fails (e.g. script read as non-UTF8), set env MKM_VAULT_ROOT
  to the vault folder or pass -VaultRoot explicitly. Save this file as UTF-8 with BOM for Korean defaults on Windows PowerShell 5.1.
#>
param(
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$VaultRoot = "G:\공유 드라이브\MKM_DATA_VAULT\vault",
    [string]$MirrorSubfolder = "notebooklm_sources",
    [switch]$WhatIf,
    [switch]$Strict
)

if (-not $PSBoundParameters.ContainsKey('VaultRoot')) {
    $e = $env:MKM_VAULT_ROOT
    if ($e -and $e.Trim()) {
        $VaultRoot = $e.Trim().TrimEnd('\')
    }
}

$ErrorActionPreference = "Stop"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

$destRoot = Join-Path $VaultRoot $MirrorSubfolder

if (-not $WhatIf) {
    if (-not (Test-Path -LiteralPath $VaultRoot)) {
        Write-Error "Vault root not found: $VaultRoot (mount shared drive or use -WhatIf)."
        exit 1
    }
    if (-not (Test-Path -LiteralPath $destRoot)) {
        New-Item -ItemType Directory -Path $destRoot -Force | Out-Null
    }
}

# Keep in sync with docs/NotebookLM_sources_manifest.md (A/B/Logos/Ijeoma blocks).
$SourceFiles = @(
    "docs\NotebookLM_sources_manifest.md",
    "docs\final\AI_MYEONGNI_MANSE_EXTERNAL_REFERENCE_LANDSCAPE_2026-03-29.md",
    "docs\final\CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
    "docs\final\master_codebook_dual_track.template.json",
    "data\regimes\regime_fusion_policy.json",
    "data\regimes\regime_map.json",
    "projects\bitcoin-trading\src\integration\dual_regime_api.py",
    "projects\bitcoin-trading\ops\v2\memory\decision_ledger.py",
    "projects\bitcoin-trading\ops\v2\memory\fact_lock_snapshot.py",
    "docs\final\LOGOS_NOTEBOOK_META_GUIDE.md",
    "docs\final\LOGOS_RISK_BRIDGE_v1.md",
    "docs\final\DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md",
    "data\logos\verse_4pipeline_full_31102.json",
    "data\logos\bible_original_hebrew_greek.jsonl",
    "data\logos\bible_original_verses.jsonl",
    "data\logos\bible_original_for_decode.jsonl",
    "data\logos\reports\ensemble_core_v1_1.csv",
    "data\logos\reports\logos_core_verses_20260315.md",
    "data\logos\reports\logos_wide_20_for_notebooklm.json",
    "data\logos\reports\logos_wide_20_for_notebooklm.csv",
    "data\logos\reports\logos_report_heb11_20260319.md",
    "data\logos\reports\logos_report_heb11_20260319.json",
    "data\logos\reports\logos_report_rom8_20260313.md",
    "data\logos\reports\logos_report_rom8_20260313.json",
    "data\logos\reports\logos_report_rom9_20260314.md",
    "data\logos\reports\logos_report_rom9_20260314.json",
    "data\logos\reports\logos_report_gen1_john1_20260319.md",
    "data\logos\reports\logos_report_gen1_john1_20260319.json",
    "data\logos\reports\logos_report_ps23_20260313.md",
    "data\logos\reports\logos_report_ps23_20260313.json",
    ".cursor\rules\logos-first-pipeline.mdc",
    "data\corpus\ijeoma\_inventory\IJEOMA_NOTEBOOKLM_QUERY_SET_2026-03-29.md",
    "data\corpus\ijeoma\_inventory\IJEOMA_INSIGHT_UNITS_XINGMING_SAMPLE_2026-03-29.json",
    "data\corpus\ijeoma\_inventory\IJEOMA_INSIGHT_UNITS_SASANG_FOUR_SAMPLE_2026-03-29.json",
    "data\corpus\ijeoma\_inventory\IJEOMA_CODEBOOK_INDEX_DRAFT_2026-03-29.json",
    "data\corpus\ijeoma\_inventory\IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json",
    "data\corpus\ijeoma\_inventory\IJEOMA_CHUNK_TABLE_2026-03-29.jsonl",
    "data\corpus\ijeoma\_inventory\IJEOMA_CORPUS_INVENTORY_2026-03-28.json",
    "data\corpus\ijeoma\_inventory\hwp_com_export_report.json",
    "data\corpus\ijeoma\e_drive_mirror\donguisusebowon_mastery_report.md"
)

$SourceDirs = @(
    "data\logos\aruljohn_kjv"
)

$copied = 0
$skipped = 0

foreach ($rel in $SourceFiles) {
    $src = Join-Path $WorkspaceRoot $rel
    $dest = Join-Path $destRoot $rel
    $destParent = Split-Path -Parent $dest

    if (-not (Test-Path -LiteralPath $src)) {
        if ($Strict) {
            throw "Missing source (Strict): $src"
        }
        Write-Warning "Skip missing: $rel"
        $skipped++
        continue
    }

    if ($WhatIf) {
        Write-Host "[WhatIf] FILE $src -> $dest"
        $copied++
        continue
    }

    if (-not (Test-Path -LiteralPath $destParent)) {
        New-Item -ItemType Directory -Path $destParent -Force | Out-Null
    }
    Copy-Item -LiteralPath $src -Destination $dest -Force
    $copied++
}

foreach ($rel in $SourceDirs) {
    $src = Join-Path $WorkspaceRoot $rel
    $dest = Join-Path $destRoot $rel

    if (-not (Test-Path -LiteralPath $src)) {
        if ($Strict) {
            throw "Missing source dir (Strict): $src"
        }
        Write-Warning "Skip missing dir: $rel"
        $skipped++
        continue
    }

    if ($WhatIf) {
        Write-Host "[WhatIf] DIR  $src -> $dest (recurse)"
        $copied++
        continue
    }

    if (Test-Path -LiteralPath $dest) {
        Remove-Item -LiteralPath $dest -Recurse -Force
    }
    $destParent = Split-Path -Parent $dest
    if (-not (Test-Path -LiteralPath $destParent)) {
        New-Item -ItemType Directory -Path $destParent -Force | Out-Null
    }
    Copy-Item -LiteralPath $src -Destination $dest -Recurse -Force
    $copied++
}

$stampLines = @(
    "sync_notebooklm_sources_to_mkm_data_vault.ps1",
    "UTC: $((Get-Date).ToUniversalTime().ToString('o'))",
    "WorkspaceRoot: $WorkspaceRoot",
    "DestRoot: $(Join-Path $VaultRoot $MirrorSubfolder)",
    "Copied operations: $copied",
    "Skipped (missing): $skipped"
)
$stampText = ($stampLines -join "`n") + "`n"

if ($WhatIf) {
    Write-Host "[WhatIf] Would write _LAST_SYNC.txt under $destRoot"
    Write-Host "Done (WhatIf). copied=$copied skipped=$skipped"
    exit 0
}

$stampPath = Join-Path $destRoot "_LAST_SYNC.txt"
Write-Utf8NoBom -Path $stampPath -Text $stampText

Write-Host "NotebookLM vault mirror OK -> $destRoot (copied=$copied skipped=$skipped)"
