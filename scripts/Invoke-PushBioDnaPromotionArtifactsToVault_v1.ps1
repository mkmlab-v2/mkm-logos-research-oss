#Requires -Version 5.1
<#
.SYNOPSIS
  Mirror DNA B-track promotion artifacts + real cohort CSVs to MKM Vault (or local fallback).

.PARAMETER WhatIfOnly
  Print planned copies without writing.
#>
[CmdletBinding()]
param(
    [switch] $WhatIfOnly
)

$ErrorActionPreference = 'Stop'
$root = 'C:\workspace'
$stamp = 'bio_dna_promotion_20260524'

$vaultTarget = $null
if (Test-Path -LiteralPath 'G:\') {
    $vaultBase = Get-ChildItem -Path 'G:\' -Directory -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq 'vault' -and $_.FullName -match 'MKM_DATA_VAULT' } |
        Select-Object -First 1
    if ($vaultBase) {
        $vaultTarget = Join-Path $vaultBase.FullName $stamp
    }
}
if (-not $vaultTarget) {
    $vaultTarget = Join-Path $root "storage\MKM_VAULT_MIRROR\$stamp"
}

$files = @(
    'tmp\bio_real_cohort_merged_with_sidecar_v1.csv',
    'tmp\bio_genotype_long_v1.csv',
    'reports\bio_paper_snp_mapping_coverage_autofill_v1.json',
    'reports\bio_dna_promotion_readiness_v1_latest.json',
    'reports\bio_dna_promotion_readiness_real_lane_v1_latest.json',
    'reports\bio_dna_promotion_threshold_sweep_v1_latest.json',
    'reports\bio_dna_constitution_promotion_packet_v1_latest.json',
    'reports\bio_dna_constitution_promotion_packet_v1_latest.md',
    'reports\bio_dna_constitution_final_approval_latest.json',
    'reports\bio_dna_btrack_promotion_hash_sealed_v1_latest.json',
    'reports\bio_dna_btrack_promotion_approval_log_v1_latest.json',
    'reports\bio_dna_ab_neutral_seed_stability_v1.json',
    'reports\bio_dna_ab_neutral_seed_stability_v1.csv',
    'reports\bio_dna_ab_holdout_eval_v1_autobuild_latest.json',
    'reports\bio_dna_ab_autobuild_report_v1_latest.json',
    'reports\bio_genotype_paper_snp_overlap_v1_latest.json',
    'reports\evidence_bundle_20260524\index.json',
    'reports\evidence_bundle_20260524\hashes_sha256.json',
    'docs\final\artifacts\bio_dna_real_cohort_restore_pointer_v1.json'
)

if (-not $WhatIfOnly) {
    New-Item -ItemType Directory -Force -Path $vaultTarget | Out-Null
}

$copied = @()
$missing = @()
foreach ($rel in $files) {
    $src = Join-Path $root $rel
    $dst = Join-Path $vaultTarget (Split-Path $rel -Leaf)
    if (-not (Test-Path -LiteralPath $src)) {
        $missing += $rel
        continue
    }
    if ($WhatIfOnly) {
        Write-Host "[PLAN] $src -> $dst"
    } else {
        Copy-Item -LiteralPath $src -Destination $dst -Force
    }
    $copied += $rel
}

$summary = [ordered]@{
    executed_at_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    schema          = 'bio_dna_vault_mirror_v1'
    target_root     = $vaultTarget
    copied_count    = $copied.Count
    copied_files    = $copied
    missing_count   = $missing.Count
    missing_files   = $missing
    fallback_used   = ($vaultTarget -notmatch 'MKM_DATA_VAULT')
}

$summaryName = '_bio_dna_mirror_summary_latest.json'
if ($WhatIfOnly) {
    Write-Host "Target: $vaultTarget"
    Write-Host "Would copy: $($copied.Count) missing: $($missing.Count)"
} else {
    ($summary | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath (Join-Path $vaultTarget $summaryName) -Encoding UTF8
    Write-Host "Bio DNA vault mirror complete. target=$vaultTarget copied=$($copied.Count) missing=$($missing.Count)"
}
