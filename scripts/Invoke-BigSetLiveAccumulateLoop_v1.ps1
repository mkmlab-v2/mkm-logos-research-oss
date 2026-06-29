#Requires -Version 5.1
<#
.SYNOPSIS
  Memory-light BigSet live accumulate loop (Azure default, rows=1 per iteration).

.DESCRIPTION
  B-track · send_gate HOLD · no Track A promotion.
  SSOT summary: reports/bigset_live_accumulate_loop_v1_latest.json

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-BigSetLiveAccumulateLoop_v1.ps1 -Iterations 3

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-BigSetLiveAccumulateLoop_v1.ps1 -Iterations 5 -SkipAzureStart
#>
param(
    [int]$Iterations = 3,
    [int]$TargetRows = 0,
    [string]$TopicSlug = "benei_haelohim_cross_refs",
    [string]$Prompt = "",
    [ValidateSet("", "theology", "nephilim")]
    [string]$PromptPreset = "",
    [int]$Rows = 1,
    [switch]$SkipAzureStart,
    [switch]$SkipIngest
)

$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "C:\workspace" }
Set-Location $Root

function Test-BigSetHealth {
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:3501/health" -TimeoutSec 5
        return ($r.status -eq "ok")
    } catch {
        return $false
    }
}

if (-not (Test-BigSetHealth)) {
    if ($SkipAzureStart) { throw "BigSet backend not healthy on :3501 and -SkipAzureStart set" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "scripts\Invoke-BigSetAzureStart_v1.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Start-Sleep -Seconds 3
    if (-not (Test-BigSetHealth)) { throw "BigSet backend still unhealthy after Azure start" }
}

$started = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$iterResults = @()
$totalAppended = 0
$okCount = 0

for ($i = 1; $i -le $Iterations; $i++) {
    if ($TargetRows -gt 0) {
        $csvPath = Join-Path $Root ("docs\research\raw\bigset_{0}_tier0_v1.csv" -f $TopicSlug)
        if (Test-Path -LiteralPath $csvPath) {
            $rowCount = (& py -c "import csv; from pathlib import Path; p=Path(r'$csvPath'); print(sum(1 for _ in csv.DictReader(p.open(encoding='utf-8-sig'))))").Trim()
            if ([int]$rowCount -ge $TargetRows) {
                Write-Host "TargetRows reached: $rowCount >= $TargetRows — stopping loop" -ForegroundColor Green
                break
            }
        }
    }
    Write-Host "== BigSet accumulate iteration $i/$Iterations (topic=$TopicSlug) ==" -ForegroundColor Cyan
    $chainArgs = @(
        "scripts/run_bigset_live_row_accumulate_chain_v1.py",
        "--live",
        "--free-tier",
        "--free-tier-mode", "azure",
        "--topic-slug", $TopicSlug,
        "--rows", "$Rows"
    )
    if ($Prompt) { $chainArgs += @("--prompt", $Prompt) }
    elseif ($PromptPreset) { $chainArgs += @("--prompt-preset", $PromptPreset) }
    if ($SkipIngest) { $chainArgs += "--skip-ingest" }

    & py @chainArgs
    $exit = $LASTEXITCODE
    $acc = $null
    $accPath = Join-Path $Root "docs\final\artifacts\bigset_tier0_csv_accumulate_v1_latest.json"
    if (Test-Path -LiteralPath $accPath) {
        $acc = Get-Content -LiteralPath $accPath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    $appended = if ($acc) { [int]$acc.rows_appended } else { 0 }
    $totalAppended += $appended
    if ($exit -eq 0) { $okCount++ }
    $iterResults += [ordered]@{
        iteration = $i
        exit_code = $exit
        rows_appended = $appended
        rows_after = if ($acc) { [int]$acc.rows_after } else { $null }
        skipped_duplicate_source_urls = if ($acc -and $acc.skipped_duplicate_source_urls) { @($acc.skipped_duplicate_source_urls) } else { @() }
    }
    if ($exit -ne 0) {
        Write-Warning "iteration $i failed exit=$exit — continuing loop"
    }
}

$summary = [ordered]@{
    schema = "bigset_live_accumulate_loop_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    started_at_utc = $started
    topic_slug = $TopicSlug
    target_rows = $TargetRows
    prompt_preset = $(if ($PromptPreset) { $PromptPreset } elseif ($Prompt) { "custom" } else { "theology" })
    iterations_requested = $Iterations
    iterations_ok = $okCount
    total_rows_appended = $totalAppended
    free_tier_mode = "azure"
    send_gate = "HOLD"
    research_only = $true
    iterations = $iterResults
    reproduce = "powershell -File scripts\Invoke-BigSetLiveAccumulateLoop_v1.ps1 -Iterations $Iterations"
}

$out = Join-Path $Root "reports\bigset_live_accumulate_loop_v1_latest.json"
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $out -Encoding UTF8
Write-Host "Wrote: $out (ok=$okCount/$Iterations appended=$totalAppended)" -ForegroundColor Green

if ($okCount -eq 0) { exit 1 }
exit 0
