param(
    [string]$SourceRoot = "C:\workspace\reports\constitution\btrack_pilot",
    [string]$VaultTargetRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourceRoot)) {
    throw "Source root not found: $SourceRoot"
}

if ([string]::IsNullOrWhiteSpace($VaultTargetRoot)) {
    $vaultBase = Get-ChildItem -Path "G:\" -Directory -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq "vault" -and $_.FullName -match "MKM_DATA_VAULT" } |
        Select-Object -First 1
    if (-not $vaultBase) {
        throw "Could not locate MKM_DATA_VAULT\\vault under G:\\"
    }
    $VaultTargetRoot = Join-Path $vaultBase.FullName "btrack_artifacts_verified"
}

if (-not (Test-Path -LiteralPath $VaultTargetRoot)) {
    New-Item -ItemType Directory -Path $VaultTargetRoot -Force | Out-Null
}

$files = @(
    "original_language_master_atoms_summary_latest.json",
    "original_language_master_atoms_latest.jsonl",
    "master_atoms_lexicon_seed_latest.jsonl",
    "master_atoms_lexicon_seed_summary_latest.json",
    "master_atoms_corpus_split_summary_latest.json",
    "morphhb_norm_to_lemma_index_latest.json",
    "master_atoms_morphhb_seed_latest.jsonl",
    "master_atoms_morphhb_seed_summary_latest.json",
    "master_atoms_step_audit_summary_latest.json",
    "master_atoms_lexicon_coverage_summary_v2_latest.json",
    "master_atoms_morphhb_match_by_corpus_latest.json",
    "canon_unmatched_top100_audit_latest.json",
    "btrack_anchor_matrix_latest.json",
    "btrack_dss_direct_slot_mapping_latest.json",
    "btrack_fusion_gate_latest.json"
)

$copied = @()
$missing = @()

foreach ($name in $files) {
    $src = Join-Path $SourceRoot $name
    $dst = Join-Path $VaultTargetRoot $name
    if (Test-Path -LiteralPath $src) {
        Copy-Item -LiteralPath $src -Destination $dst -Force
        $copied += $name
    } else {
        $missing += $name
    }
}

$summary = [ordered]@{
    executed_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    source_root = $SourceRoot
    target_root = $VaultTargetRoot
    copied_count = $copied.Count
    copied_files = $copied
    missing_count = $missing.Count
    missing_files = $missing
}

$summaryPath = Join-Path $VaultTargetRoot "_push_summary_latest.json"
($summary | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $summaryPath -Encoding UTF8

Write-Host "Artifact push complete. copied=$($copied.Count) missing=$($missing.Count)"
Write-Host "Target: $VaultTargetRoot"
