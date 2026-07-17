param(
    [string]$SourceRoot = "C:\workspace\reports\constitution\btrack_pilot",
    [string]$VaultTargetRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourceRoot)) {
    throw "Source root not found: $SourceRoot"
}

function Resolve-VaultTargetRoot {
    param([string]$ExplicitTarget)

    if (-not [string]::IsNullOrWhiteSpace($ExplicitTarget)) {
        return $ExplicitTarget.Trim().TrimEnd('\')
    }

    # Prefer MKM_VAULT_ROOT (same wall as run_workspace_automation_health.ps1).
    $vault = $env:MKM_VAULT_ROOT
    if ([string]::IsNullOrWhiteSpace($vault)) {
        $vault = "G:\공유 드라이브\MKM_DATA_VAULT\vault"
    } else {
        $vault = $vault.Trim().TrimEnd('\')
    }

    # Test-Path before Join-Path: Join-Path throws if drive letter is missing.
    if (Test-Path -LiteralPath $vault) {
        return (Join-Path $vault "btrack_artifacts_verified")
    }

    # G: discovery fallback (legacy behavior) — only when drive is mounted.
    if (Test-Path -LiteralPath "G:\") {
        $vaultBase = Get-ChildItem -Path "G:\" -Directory -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -eq "vault" -and $_.FullName -match "MKM_DATA_VAULT" } |
            Select-Object -First 1
        if ($vaultBase) {
            return (Join-Path $vaultBase.FullName "btrack_artifacts_verified")
        }
    }

    return $null
}

if ([string]::IsNullOrWhiteSpace($VaultTargetRoot)) {
    $resolved = Resolve-VaultTargetRoot -ExplicitTarget ""
    if (-not $resolved) {
        $vaultHint = if ([string]::IsNullOrWhiteSpace($env:MKM_VAULT_ROOT)) {
            "G:\공유 드라이브\MKM_DATA_VAULT\vault"
        } else {
            $env:MKM_VAULT_ROOT.Trim().TrimEnd('\')
        }
        Write-Host "SKIP: Vault not mounted ($vaultHint) - no push (not a C: fake vault)."
        exit 0
    }
    $VaultTargetRoot = $resolved
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
