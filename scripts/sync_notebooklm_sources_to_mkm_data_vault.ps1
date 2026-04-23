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

.PARAMETER IncludeObsidianContext
  Also mirror selected `memory/obsidian_vault` subtrees into `<VaultRoot>/obsidian_context/` as `*.md` only,
  excluding `.obsidian` and `_cursor_session_staging`. SSOT: docs/NotebookLM_sources_manifest.md (B 보조 — Obsidian Context).

.PARAMETER ObsidianVaultRoot
  Absolute path to the Obsidian vault root (folder that contains `00_Project_Core`, etc.). When omitted, uses env
  `MKM_OBSIDIAN_VAULT_ROOT` if set; otherwise `<WorkspaceRoot>/memory/obsidian_vault`. If that default path is missing,
  it is created (stub dirs only) so mirrors do not spam per-folder warnings.

.PARAMETER Strict
  Fail if any listed source path is missing.

  If -VaultRoot is omitted and the default path fails (e.g. script read as non-UTF8), set env MKM_VAULT_ROOT
  to the vault folder or pass -VaultRoot explicitly. Save this file as UTF-8 with BOM for Korean defaults on Windows PowerShell 5.1.

.NOTES
  Paths listed in $OptionalMissingRel may be absent in a minimal clone (not in git, VPS-only, or under .gitignore);
  those skips use Write-Host instead of Write-Warning. See docs/NotebookLM_sources_manifest.md.
#>
param(
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$VaultRoot = "G:\공유 드라이브\MKM_DATA_VAULT\vault",
    [string]$MirrorSubfolder = "notebooklm_sources",
    [switch]$WhatIf,
    [switch]$Strict,
    [switch]$IncludeObsidianContext,
    [string]$ObsidianVaultRoot = ""
)

if (-not $PSBoundParameters.ContainsKey('VaultRoot')) {
    $e = $env:MKM_VAULT_ROOT
    if ($e -and $e.Trim()) {
        $VaultRoot = $e.Trim().TrimEnd('\')
    }
}

# Obsidian mirror source (vault folder containing manifest subdirs); same pattern as MKM_VAULT_ROOT.
$obsidianVaultResolved = ""
if ($PSBoundParameters.ContainsKey('ObsidianVaultRoot') -and $ObsidianVaultRoot.Trim()) {
    $obsidianVaultResolved = $ObsidianVaultRoot.Trim().TrimEnd('\')
} elseif ($env:MKM_OBSIDIAN_VAULT_ROOT -and $env:MKM_OBSIDIAN_VAULT_ROOT.Trim()) {
    $obsidianVaultResolved = $env:MKM_OBSIDIAN_VAULT_ROOT.Trim().TrimEnd('\')
} else {
    $obsidianVaultResolved = Join-Path $WorkspaceRoot "memory\obsidian_vault"
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
    "docs\final\CURRENT_OPS_SNAPSHOT.md",
    "docs\final\AI_MYEONGNI_MANSE_EXTERNAL_REFERENCE_LANDSCAPE_2026-03-29.md",
    "docs\final\CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
    "docs\final\MKM12_PRISM_INDEX_REGISTRY_V1.json",
    "docs\final\COMPRESSION_SLA_POLICY_V1.md",
    "docs\final\COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
    "docs\final\COMPRESSION_EVALUATE_REPORT_DATA_FLOW_V1.md",
    "docs\final\MKM_LESSONS_LEARNED_V1.md",
    "docs\final\COMPRESSION_RESTORATION_EVOLUTION_INDEX_V1.md",
    "docs\final\MKM_CORE_THEORY_V1.md",
    "docs\final\RESEARCH_HISTORY_V1.md",
    "docs\final\openapi_token_compression_stub_v1.yaml",
    "docs\final\STATE16_INTERFACE_INSERTION_CONTRACT_2026-03-31.md",
    "docs\final\MASTER_Linguistic_Contract_2026.md",
    "docs\final\master_codebook_dual_track.template.json",
    "data\regimes\regime_fusion_policy.json",
    "data\regimes\regime_map.json",
    "data\regimes\btc_regime_map.json",
    "projects\bitcoin-trading\src\integration\dual_regime_api.py",
    "projects\bitcoin-trading\ops\v2\memory\decision_ledger.py",
    "projects\bitcoin-trading\ops\v2\memory\fact_lock_snapshot.py",
    "docs\final\LOGOS_NOTEBOOK_META_GUIDE.md",
    "docs\final\P0_COMMERCIALIZATION_TRACKER.md",
    "docs\final\LOGOS_RISK_BRIDGE_v1.md",
    "projects\bitcoin-trading\ops\v2\README.md",
    "projects\bitcoin-trading\ops\windows-rehearsal\WAITING_QUEUE_DUAL_BTC_RUNBOOK.md",
    "projects\bitcoin-trading\ops\windows-rehearsal\DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md",
    "docs\final\DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md",
    "docs\final\artifacts\LOGOS_STATE_MAPPING_V1.json",
    "docs\final\artifacts\LOGOS_STATE_MAPPING_V2.json",
    "docs\final\artifacts\LOGOS_STATE_MAPPING_TRACKA_GATE_V1.json",
    "docs\final\artifacts\LOGOS_STATE_MAPPING_DELTA_REPORT_V1.json",
    "docs\final\artifacts\LOGOS_STATE_MAPPING_RELEASE_GATE_V1.json",
    "docs\final\artifacts\CROSS_REF_DSS_TO_STATES_DRAFT.json",
    "docs\final\artifacts\B_TRACK_HYPOTHESIS_INVENTORY_V1.json",
    "projects\dss-4d-ingest\outputs\unified_frontline_cycle_report_command_center_followup_20260327_f.json",
    "docs\final\NOTEBOOKLM_DSS_APOCRYPHA_BUNDLE_NOTE_command_center_followup_20260327_f.md",
    "data\logos\verse_4pipeline_full_31102.json",
    "data\logos\bible_original_hebrew_greek.jsonl",
    "data\logos\bible_original_verses.jsonl",
    "data\logos\bible_original_for_decode.jsonl",
    "data\logos\reports\ensemble_core_v1_1.csv",
    "data\logos\reports\logos_core_verses_20260315.md",
    "data\logos\reports\logos_wide_20_for_notebooklm.json",
    "data\logos\reports\logos_wide_20_for_notebooklm.csv",
    "backtest_results\LOGOS_RESONANCE_BTC_BULL_FULL.json",
    "backtest_results\LOGOS_RESONANCE_BTC_BEAR_FULL.json",
    "backtest_results\LOGOS_RESONANCE_BTC_SIDEWAYS_FULL.json",
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
    "data\corpus\ijeoma\e_drive_mirror\donguisusebowon_mastery_report.md",
    "docs\final\artifacts\BLIND_REPLAY_PROXY_PROFILE_D_PARAMS_V1.json",
    "docs\final\artifacts\BLIND_REPLAY_PROXY_PROFILE_D_ENSEMBLE_SEARCH_V1.json",
    "docs\final\artifacts\aegis_unified_scoreboard_abcds_latest.json",
    "docs\final\artifacts\aegis_unified_scoreboard_btc90_k010_latest.json",
    "docs\final\artifacts\BLIND_REPLAY_C1_ARTIFACT_BUNDLE_2026-04-02.md",
    "reports\constitution\btrack_pilot\blind_replay\blind_replay_dataset_grid_btc_s80_latest.json",
    "reports\constitution\btrack_pilot\blind_replay\blind_replay_dataset_grid_kospi_s80_latest.json",
    "docs\final\NOTEBOOKLM_OPS_COMMAND_BRIEF_LOGOS_SHADOW_2026-04-03.md",
    "docs\final\artifacts\LOGOS_SHADOW_202003_INSIGHT_BRIEF_V1.md",
    "docs\final\artifacts\logos_kospi_shadow_evaluation_bundle_v23_notebooklm.md",
    "reports\research\logos_shadow_v1\logos_kospi_shadow_evaluation_bundle_v23_latest.json",
    "reports\research\logos_shadow_v1\logos_kospi_shadow_ablation_v23_round1_summary.json",
    "docs\final\NOTEBOOKLM_HUB_B_BTC_AB_TRACK_CROSSCHECK_BRIEF_2026-04-04.md",
    "docs\final\SWARM_SENTIMENT_METRIC_SCHEMA_DRAFT.json",
    "docs\final\dummy_swarm_score.jsonl",
    "docs\final\hypo_test_sentiment.jsonl",
    "docs\final\corr_report_001_hypo.jsonl",
    "docs\final\corr_report_001_left_lens.json",
    "docs\final\SWARM_SENTIMENT_METRIC_NOTEBOOKLM_BUNDLE_2026-04-04.md",
    "docs\final\NOTEBOOKLM_MKMLIFE_NEWS_QUESTION_STARTER_BUNDLE_2026-04-12.md",
    "docs\final\NOTEBOOKLM_LOG_METABOLISM_CORE_BRIDGE_POINTER_V1.md",
    "docs\final\TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md",
    "docs\final\artifacts\news_question_starter_sample_v1.json",
    "docs\final\artifacts\gematria_myeongri_corpus_delta_apocrypha_v1.json",
    "docs\final\artifacts\gematria_myeongri_corpus_delta_dss_v1.json",
    "docs\final\artifacts\gematria_myeongri_corpus_delta_unified_summary_v1.json",
    "docs\final\artifacts\original_corpus_regime_singularity_report_v1.json",
    "docs\final\artifacts\original_corpus_regime_singularity_report_with_canon_v1.json",
    "docs\final\artifacts\original_corpus_regime_singularity_canon_only_v1.json",
    "docs\final\artifacts\original_corpus_regime_singularity_canon_lane_summary_v1.json",
    "docs\final\artifacts\original_corpus_regime_singularity_canon_quality_gate_v1.json",
    "docs\final\artifacts\regime_map_calibration_round2_for_sideways_v1.json",
    "docs\final\artifacts\regime_map_calibration_round3_balanced_constraints_v1.json",
    "docs\final\artifacts\regime_map_calibration_round4_mixed_hybrid_v1.json",
    "docs\final\artifacts\original_corpus_regime_singularity_balanced_report_v1.json",
    "docs\final\artifacts\original_corpus_regime_singularity_balanced_report_with_canon_v1.json",
    "docs\final\artifacts\original_corpus_regime_singularity_balanced_canon_only_v1.json",
    "docs\final\artifacts\btrack_balanced_regime_eval_latest.json",
    "docs\final\artifacts\btrack_balanced_regime_eval_baseline_v1.json",
    "docs\final\artifacts\original_singularity_gloss_report_v3.json",
    "docs\final\artifacts\original_singularity_gloss_report_v4.json",
    "docs\final\artifacts\hebrew_singularity_gloss_overrides_v1.json",
    "docs\final\artifacts\master_codebook_lexicon_v1_export_pointer_latest.json"
)

$SourceDirs = @(
    "data\logos\aruljohn_kjv"
)

# Same strings as $SourceFiles; absent in many clones — document in NotebookLM_sources_manifest.md
$OptionalMissingRel = [string[]]@(
    "projects\bitcoin-trading\ops\v2\memory\decision_ledger.py",
    "projects\bitcoin-trading\ops\v2\memory\fact_lock_snapshot.py",
    "projects\bitcoin-trading\ops\windows-rehearsal\WAITING_QUEUE_DUAL_BTC_RUNBOOK.md",
    "projects\bitcoin-trading\ops\windows-rehearsal\DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md",
    "backtest_results\LOGOS_RESONANCE_BTC_BULL_FULL.json",
    "backtest_results\LOGOS_RESONANCE_BTC_BEAR_FULL.json",
    "backtest_results\LOGOS_RESONANCE_BTC_SIDEWAYS_FULL.json"
)

$copied = 0
$skipped = 0
$obsidianCopied = 0

foreach ($rel in $SourceFiles) {
    $src = Join-Path $WorkspaceRoot $rel
    $dest = Join-Path $destRoot $rel
    $destParent = Split-Path -Parent $dest

    if (-not (Test-Path -LiteralPath $src)) {
        if ($Strict) {
            throw "Missing source (Strict): $src"
        }
        if ($OptionalMissingRel -contains $rel) {
            Write-Host "Skip optional (not in workspace): $rel" -ForegroundColor DarkGray
        } else {
            Write-Warning "Skip missing: $rel"
        }
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

    if (-not (Test-Path -LiteralPath $dest)) {
        New-Item -ItemType Directory -Path $dest -Force | Out-Null
    }
    # Mirror directory content with robocopy to avoid transient Remove-Item failures on G: shares.
    # robocopy exit codes 0-7 are success variants (copied/mismatch/extras handled).
    $null = & robocopy $src $dest /MIR /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
    $rc = $LASTEXITCODE
    if ($rc -gt 7) {
        throw "robocopy failed for dir '$rel' with exit code $rc"
    }
    $copied++
}

# Optional: Obsidian -> <VaultRoot>/obsidian_context (*.md only; see NotebookLM_sources_manifest.md)
if ($IncludeObsidianContext) {
    $ObsidianSubdirs = @(
        "00_Project_Core",
        "raw_research",
        "OPS",
        "SPIRIT",
        "TRADING",
        "CODING",
        "RESEARCH",
        "LOGIC",
        "KNOWLEDGE"
    )
    $obsidianDestRoot = Join-Path $VaultRoot "obsidian_context"
    $defaultWsObsidianVault = Join-Path $WorkspaceRoot "memory\obsidian_vault"
    $notebookLmRootMds = @()

    if (-not (Test-Path -LiteralPath $obsidianVaultResolved)) {
        if ($obsidianVaultResolved -eq $defaultWsObsidianVault) {
            New-Item -ItemType Directory -Path $obsidianVaultResolved -Force | Out-Null
            foreach ($sd in $ObsidianSubdirs) {
                $sdPath = Join-Path $obsidianVaultResolved $sd
                if (-not (Test-Path -LiteralPath $sdPath)) {
                    New-Item -ItemType Directory -Path $sdPath -Force | Out-Null
                }
            }
        } else {
            Write-Warning "Obsidian vault root not found (set MKM_OBSIDIAN_VAULT_ROOT or -ObsidianVaultRoot): $obsidianVaultResolved — skipping Obsidian context mirror."
        }
    }

    # Partial clone: vault root exists but manifest subdirs missing — fill stubs only under workspace default path.
    if ((Test-Path -LiteralPath $obsidianVaultResolved) -and ($obsidianVaultResolved -eq $defaultWsObsidianVault)) {
        foreach ($sd in $ObsidianSubdirs) {
            $sdPath = Join-Path $obsidianVaultResolved $sd
            if (-not (Test-Path -LiteralPath $sdPath)) {
                New-Item -ItemType Directory -Path $sdPath -Force | Out-Null
            }
        }
    }

    if (Test-Path -LiteralPath $obsidianVaultResolved) {
        $notebookLmRootMds = @(Get-ChildItem -LiteralPath $obsidianVaultResolved -Filter "NotebookLM*.md" -File -ErrorAction SilentlyContinue)
    }

    if (-not $WhatIf) {
        if (-not (Test-Path -LiteralPath $VaultRoot)) {
            Write-Error "Vault root not found for Obsidian mirror: $VaultRoot"
            exit 1
        }
        if (-not (Test-Path -LiteralPath $obsidianDestRoot)) {
            New-Item -ItemType Directory -Path $obsidianDestRoot -Force | Out-Null
        }
    }

    foreach ($short in $ObsidianSubdirs) {
        $src = Join-Path $obsidianVaultResolved $short
        if (-not (Test-Path -LiteralPath $src)) {
            continue
        }
        $dest = Join-Path $obsidianDestRoot $short
        if ($WhatIf) {
            Write-Host "[WhatIf] OBSIDIAN_MD $src -> $dest (*.md /S, exclude .obsidian, _cursor_session_staging)"
            $obsidianCopied++
            continue
        }
        if (-not (Test-Path -LiteralPath $dest)) {
            New-Item -ItemType Directory -Path $dest -Force | Out-Null
        }
        $null = & robocopy $src $dest *.md /S /XD .obsidian _cursor_session_staging /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
        $rc = $LASTEXITCODE
        if ($rc -gt 7) {
            throw "robocopy failed for Obsidian dir '$short' with exit code $rc"
        }
        $obsidianCopied++
    }

    foreach ($fi in $notebookLmRootMds) {
        $src = $fi.FullName
        $leaf = $fi.Name
        $dest = Join-Path $obsidianDestRoot $leaf
        if ($WhatIf) {
            Write-Host "[WhatIf] OBSIDIAN_FILE $src -> $dest"
            $obsidianCopied++
            continue
        }
        $destParent = Split-Path -Parent $dest
        if (-not (Test-Path -LiteralPath $destParent)) {
            New-Item -ItemType Directory -Path $destParent -Force | Out-Null
        }
        Copy-Item -LiteralPath $src -Destination $dest -Force
        $obsidianCopied++
    }

    Write-Host "Obsidian context mirror -> $obsidianDestRoot (source=$obsidianVaultResolved operations=$obsidianCopied)"
}

$stampLines = @(
    "sync_notebooklm_sources_to_mkm_data_vault.ps1",
    "UTC: $((Get-Date).ToUniversalTime().ToString('o'))",
    "WorkspaceRoot: $WorkspaceRoot",
    "DestRoot: $(Join-Path $VaultRoot $MirrorSubfolder)",
    "Copied operations: $copied",
    "Skipped (missing): $skipped",
    "IncludeObsidianContext: $IncludeObsidianContext",
    "ObsidianVaultRoot: $obsidianVaultResolved",
    "Obsidian context operations: $obsidianCopied"
)
$stampText = ($stampLines -join "`n") + "`n"

if ($WhatIf) {
    Write-Host "[WhatIf] Would write _LAST_SYNC.txt under $destRoot"
    Write-Host "Done (WhatIf). copied=$copied skipped=$skipped"
    exit 0
}

$stampPath = Join-Path $destRoot "_LAST_SYNC.txt"
Write-Utf8NoBom -Path $stampPath -Text $stampText

Write-Host "NotebookLM vault mirror OK -> $destRoot (copied=$copied skipped=$skipped; optional-absent uses gray line, unexpected absent uses WARNING)"
