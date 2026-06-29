<#
.SYNOPSIS
  C: workspace Phase3 — cold-archive stale report dirs to F: + git gc aggressive + HF env SSOT.

.NOTES
  [HYPO] infra lane · research_only · no Track A / live coupling.
  Nemotron 106G + storage/adapters remain on C: (active path refs).
#>
param(
    [switch]$WhatIfOnly,
    [string]$ColdRoot = "F:\workspace_cold_storage\reports_archive"
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
Set-Location $root

$outJson = Join-Path $root "reports\c_workspace_phase3_cold_archive_v1_latest.json"
$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$steps = [System.Collections.Generic.List[object]]::new()

function Add-Step($name, $exitCode, $note) {
    $script:steps.Add([ordered]@{
        name      = $name
        exit_code = $exitCode
        note      = $note
    }) | Out-Null
}

$coldDirs = @(
    "reports\kaggle_nemotron_run_v8_output",
    "reports\kaggle_nemotron_run_v9_output",
    "reports\kaggle_nemotron_run_v10_output",
    "reports\kaggle_nemotron_run_v12_output",
    "reports\kaggle_nemotron_run_v13_output",
    "reports\kaggle_nemotron_run_v14_logonly",
    "reports\kaggle_nemotron_run_v15_logonly",
    "reports\kaggle_nemotron_run_v16_logonly",
    "reports\kaggle_nemotron_v17_log",
    "reports\logos_edge_hypothesis_microtrain_v1",
    "reports\logos_edge_hypothesis_microtrain_covenant_rank_emphasis_v1",
    "reports\logos_edge_hypothesis_lora_adapter_offline_4d_strict_rank_emphasis_v1",
    "reports\logos_edge_hypothesis_microtrain_offline_4d_strict_v1",
    "reports\logos_edge_hypothesis_microtrain_rank_emphasis_v1"
)

$junctionDirs = @(
    "reports\lora_stub_adapters_v1"
)

$movedBytes = 0
$junctionResults = @()

if (-not $WhatIfOnly) {
    New-Item -ItemType Directory -Path $ColdRoot -Force | Out-Null
}

Write-Host "[1/4] cold-archive report dirs -> $ColdRoot" -ForegroundColor Cyan
foreach ($rel in $coldDirs) {
    $src = Join-Path $root $rel
    if (-not (Test-Path -LiteralPath $src)) {
        continue
    }
    $dest = Join-Path $ColdRoot (Split-Path $rel -Leaf)
    if ($WhatIfOnly) {
        Write-Host "  whatif MOVE $rel"
        continue
    }
    if (Test-Path -LiteralPath $dest) {
        Write-Host "  skip (dest exists): $rel"
        continue
    }
    robocopy $src $dest /E /MOVE /R:1 /W:2 /NFL /NDL /NP | Out-Null
    $rc = $LASTEXITCODE
    if ($rc -ge 8) {
        Add-Step "cold_move_$($rel -replace '\\','_')" $rc "robocopy_failed"
        continue
    }
    $left = @(Get-ChildItem -LiteralPath $src -Recurse -File -Force -ErrorAction SilentlyContinue).Count
    if ($left -eq 0) {
        Remove-Item -LiteralPath $src -Recurse -Force -ErrorAction SilentlyContinue
    }
    Add-Step "cold_move_$($rel -replace '\\','_')" 0 "dest=$dest leftover_files=$left"
}

Write-Host "[2/4] junction cold dirs (stub adapters)" -ForegroundColor Cyan
foreach ($rel in $junctionDirs) {
    $src = Join-Path $root $rel
    if (-not (Test-Path -LiteralPath $src)) {
        continue
    }
    $dest = Join-Path $ColdRoot (Split-Path $rel -Leaf)
    if ($WhatIfOnly) {
        Write-Host "  whatif JUNCTION $rel -> $dest"
        continue
    }
    if (-not (Test-Path -LiteralPath $dest)) {
        robocopy $src $dest /E /MOVE /R:1 /W:2 /NFL /NDL /NP | Out-Null
        if ($LASTEXITCODE -ge 8) {
            Add-Step "junction_move_$($rel -replace '\\','_')" $LASTEXITCODE "robocopy_failed"
            continue
        }
        Remove-Item -LiteralPath $src -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path -LiteralPath $src)) {
        cmd /c mklink /J $src $dest | Out-Null
        $junctionResults += [ordered]@{ path = $rel; target = $dest; ok = (Test-Path -LiteralPath $src) }
    }
    Add-Step "junction_$($rel -replace '\\','_')" 0 "target=$dest"
}

Write-Host "[3/4] git gc --aggressive" -ForegroundColor Cyan
if ($WhatIfOnly) {
    Add-Step "git_gc_aggressive" 0 "whatif_skipped"
} else {
    git gc --aggressive --prune=now 2>&1 | Out-Null
    Add-Step "git_gc_aggressive" $LASTEXITCODE "prune_now"
}

Write-Host "[4/4] HF user env -> F:\workspace_offload" -ForegroundColor Cyan
$hfHome = "F:\workspace_offload\hf_cache\huggingface"
$hfHub = "F:\workspace_offload\hf_cache\huggingface\hub"
if ($WhatIfOnly) {
    Add-Step "hf_env_user" 0 "whatif_skipped"
} else {
    [Environment]::SetEnvironmentVariable("HF_HOME", $hfHome, "User")
    [Environment]::SetEnvironmentVariable("HF_HUB_CACHE", $hfHub, "User")
    [Environment]::SetEnvironmentVariable("HUGGINGFACE_HUB_CACHE", $hfHub, "User")
    Add-Step "hf_env_user" 0 "HF_HOME=$hfHome"
}

$cFree = [math]::Round((Get-Volume -DriveLetter C).SizeRemaining / 1GB, 1)
$doc = [ordered]@{
    schema           = "c_workspace_phase3_cold_archive_v1"
    generated_at_utc = $utc
    research_only    = $true
    hypothesis_tag   = "[HYPO]"
    cold_root        = $ColdRoot
    phase3_actions   = $steps
    junctions        = $junctionResults
    c_free_gb        = $cFree
    holds            = @(
        "data/nvidia + storage/hf_cache/nemotron_wsl (WSL)",
        "storage/adapters (active LoRA path refs)"
    )
    boundary_ack     = "B→A·실매매 자동 합선 없음"
}

if (-not $WhatIfOnly) {
    ($doc | ConvertTo-Json -Depth 6) | Set-Content -Path $outJson -Encoding utf8
    Write-Host "Wrote $outJson" -ForegroundColor Green
    Write-Host "C: free ${cFree} GB" -ForegroundColor Green
}

$fail = ($steps | Where-Object { $_.exit_code -ne 0 -and $_.exit_code -lt 8 }).Count
if ($fail -gt 0) { exit 1 }
exit 0
