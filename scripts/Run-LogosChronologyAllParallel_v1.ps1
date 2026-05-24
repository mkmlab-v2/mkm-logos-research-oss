# Omni-parallel: tier AB + narrative AB/hardset v1 + hardset v2 (compute parallel, merge once).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosChronologyAllParallel_v1.ps1
# Optional: -SkipBundle (skip Invoke-LogosChronologyParallelBundle overlay/deploy)

param(
    [switch]$SkipBundle,
    [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$goldHist = "$root\docs\final\artifacts\fixtures\logos_chronology_historical_era_gold_v1.json"

function Invoke-PyStep {
    param([string]$Label, [string[]]$PyArgs)
    Write-Host "==> $Label"
    & $py @PyArgs
    if ($LASTEXITCODE -ne 0) { throw "$Label failed exit=$LASTEXITCODE" }
}

$trackTier = {
    Set-Location $using:root
    $py = $using:py
    $goldHist = $using:goldHist
    $root = $using:root
    & $py "$root\scripts\run_logos_chronology_era_tier_boost_ab_v1.py"
    if ($LASTEXITCODE -ne 0) { throw "tier AB" }
    & $py "$root\scripts\eval_logos_chronology_era_blind_v1.py" `
        --gold-json $goldHist --tag-mode gold_tags --modern-boost 0.08 --boost-policy tier_v1 `
        --output-json "$root\docs\final\artifacts\logos_chronology_era_blind_eval_v1_latest.json"
    if ($LASTEXITCODE -ne 0) { throw "tier eval" }
    Copy-Item -LiteralPath "$root\docs\final\artifacts\logos_chronology_era_blind_eval_v1_latest.json" `
        -Destination "$root\docs\final\artifacts\logos_chronology_era_blind_eval_tier_v1_latest.json" -Force
}

$trackNarrative = {
    Set-Location $using:root
    $py = $using:py
    $root = $using:root
    & $py "$root\scripts\build_logos_hardset_news_era_gold_v1.py"
    if ($LASTEXITCODE -ne 0) { throw "hardset v1 gold" }
    & $py "$root\scripts\run_logos_chronology_era_modern_boost_ab_v1.py"
    if ($LASTEXITCODE -ne 0) { throw "modern_boost AB" }
    & $py "$root\scripts\eval_logos_chronology_era_blind_v1.py" `
        --gold-json "$root\docs\final\artifacts\logos_chronology_hardset_news_era_gold_v1_latest.json" `
        --tag-mode text_blind --modern-boost 0 `
        --output-json "$root\docs\final\artifacts\logos_chronology_hardset_text_blind_eval_v1_latest.json"
    if ($LASTEXITCODE -ne 0) { throw "hardset v1 eval" }
}

$trackHardsetV2 = {
    Set-Location $using:root
    $py = $using:py
    $root = $using:root
    & $py "$root\scripts\build_logos_hardset_news_era_gold_v2_v1.py"
    if ($LASTEXITCODE -ne 0) { throw "hardset v2 gold" }
    & $py "$root\scripts\run_logos_hardset_gold_mode_compare_v1.py"
    if ($LASTEXITCODE -ne 0) { throw "hardset compare" }
    & $py "$root\scripts\eval_logos_chronology_era_blind_v1.py" `
        --gold-json "$root\docs\final\artifacts\logos_chronology_hardset_news_era_gold_v2_latest.json" `
        --tag-mode text_blind --modern-boost 0.08 --boost-policy tier_v1 `
        --output-json "$root\docs\final\artifacts\logos_chronology_hardset_text_blind_v2_eval_v1_latest.json"
    if ($LASTEXITCODE -ne 0) { throw "hardset v2 eval" }
}

Write-Host "[omni] phase 1: 3 tracks in parallel (tier / narrative+hardset v1 / hardset v2)"
$j1 = Start-Job -Name TierBoost -ScriptBlock $trackTier
$j2 = Start-Job -Name NarrativeAB -ScriptBlock $trackNarrative
$j3 = Start-Job -Name HardsetV2 -ScriptBlock $trackHardsetV2
Wait-Job -Job $j1, $j2, $j3 | Out-Null
foreach ($j in @($j1, $j2, $j3)) {
    if ($j.State -eq "Failed") {
        Receive-Job -Job $j -ErrorAction SilentlyContinue | Write-Host
        throw "Job $($j.Name) failed"
    }
    Receive-Job -Job $j | Write-Host
    Remove-Job -Job $j
}

Write-Host "[omni] phase 2: historical eval (serial, shared chronology)"
Invoke-PyStep "historical gold_tags tier_v1" @(
    "$root\scripts\eval_logos_chronology_era_blind_v1.py",
    "--gold-json", $goldHist, "--tag-mode", "gold_tags",
    "--modern-boost", "0.08", "--boost-policy", "tier_v1",
    "--output-json", "$root\docs\final\artifacts\logos_chronology_era_blind_eval_v1_latest.json"
)
Invoke-PyStep "historical text_blind" @(
    "$root\scripts\eval_logos_chronology_era_blind_v1.py",
    "--gold-json", $goldHist, "--tag-mode", "text_blind",
    "--output-json", "$root\docs\final\artifacts\logos_chronology_era_blind_eval_text_blind_v1_latest.json"
)

Write-Host "[omni] phase 3: dynamic map + merge + digest"
Invoke-PyStep "dynamic map" @("$root\scripts\build_logos_chronology_dynamic_map_v1.py")
Invoke-PyStep "revalidation merge" @("$root\scripts\merge_logos_symbolic_revalidation_era_blocks_v1.py")
Invoke-PyStep "operator digest" @("$root\scripts\build_logos_chronology_era_eval_digest_v1.py")

if (-not $SkipPytest) {
    Write-Host "[omni] phase 4: pytest"
    & $py -m pytest `
        tests/test_eval_logos_chronology_era_blind_v1.py `
        tests/test_logos_chronology_hardset_and_ab_v1.py `
        tests/test_logos_chronology_tier_boost_v1.py `
        tests/test_logos_chronology_hardset_gold_v2_v1.py -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipBundle) {
    Write-Host "[omni] phase 5: showroom bundle (era eval skipped — already ran)"
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$root\scripts\Invoke-LogosChronologyParallelBundle_v1.ps1" `
        -WorkspaceRoot $root -SkipEraBlindEval
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "OK: Logos chronology omni-parallel complete"
