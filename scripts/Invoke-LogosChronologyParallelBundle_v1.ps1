# Chronology overlay -> MVP copy -> deploy staging -> optional VPS sync (oracle v3).
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-LogosChronologyParallelBundle_v1.ps1
#   ... -ChronologyJson docs\final\artifacts\logos_chronology_v1_latest.json
#   ... -SkipVpsSync

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$ChronologyJson = "",
    [switch]$SkipVpsSync,
    [switch]$ApplyRecommendedNginx,
    [switch]$RebuildChronology,
    [switch]$SkipEraBlindEval
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path

$applyPy = Join-Path $root "scripts\apply_logos_chronology_to_graph_v1.py"
$overlayLatest = Join-Path $root "docs\final\artifacts\logos_chronology_showroom_overlay_v1_latest.json"
$mvpOverlay = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp\showroom_logos_chronology_overlay_v1.json"
$deploy = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\deploy_showroom_static.ps1"
$sync = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\sync_showroom_to_vps.ps1"

$chronoPath = if (-not [string]::IsNullOrWhiteSpace($ChronologyJson)) {
    (Resolve-Path -LiteralPath $ChronologyJson).Path
} else {
    Join-Path $root "docs\final\artifacts\logos_chronology_v1_latest.json"
}

# WARNING: -RebuildChronology overwrites logos_chronology_v1_latest.json with 5-era SSOT stub.
# After AI v2 or commander override, do NOT pass -RebuildChronology unless intentional rollback.
Write-Host "[logos-chrono-bundle] (0/4) build chronology from repo SSOT (if missing or -RebuildChronology)"
$buildPy = Join-Path $root "scripts\build_logos_chronology_from_repo_ssot_v1.py"
if (-not (Test-Path -LiteralPath $chronoPath) -or $RebuildChronology) {
    & py $buildPy --out $chronoPath
    if ($LASTEXITCODE -ne 0) { throw "build_logos_chronology_from_repo_ssot_v1.py failed: $LASTEXITCODE" }
}

$dynamicMapPy = Join-Path $root "scripts\build_logos_chronology_dynamic_map_v1.py"
$eraFullPs1 = Join-Path $root "scripts\Run-LogosChronologyEraBlindEvalFull_v1.ps1"
$digestPy = Join-Path $root "scripts\build_logos_chronology_era_eval_digest_v1.py"

Write-Host "[logos-chrono-bundle] (0a) dynamic map from macro tags"
& py $dynamicMapPy
if ($LASTEXITCODE -ne 0) { throw "build_logos_chronology_dynamic_map_v1.py failed: $LASTEXITCODE" }

if (-not $SkipEraBlindEval) {
    Write-Host "[logos-chrono-bundle] (0b) era blind eval full chain"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $eraFullPs1
    if ($LASTEXITCODE -ne 0) { throw "Run-LogosChronologyEraBlindEvalFull_v1.ps1 failed: $LASTEXITCODE" }
    & py $digestPy
    if ($LASTEXITCODE -ne 0) { throw "build_logos_chronology_era_eval_digest_v1.py failed: $LASTEXITCODE" }
    $horizon2030Py = Join-Path $root "scripts\build_logos_macro_horizon_2030_scenario_v1.py"
    Write-Host "[logos-chrono-bundle] (0c) macro horizon 2030 scenario (strict)"
    & py $horizon2030Py --strict
    if ($LASTEXITCODE -ne 0) { throw "build_logos_macro_horizon_2030_scenario_v1.py failed: $LASTEXITCODE" }
} else {
    Write-Host "[logos-chrono-bundle] era blind eval skipped (-SkipEraBlindEval)"
}

Write-Host "[logos-chrono-bundle] (1/4) apply chronology -> overlay JSON"
$applyArgs = @($applyPy, "--chronology-json", $chronoPath)
& py @applyArgs
if ($LASTEXITCODE -ne 0) { throw "apply_logos_chronology_to_graph_v1.py failed: $LASTEXITCODE" }

Write-Host "[logos-chrono-bundle] (2/4) copy overlay -> jemaai-cloud-mvp"
Copy-Item -LiteralPath $overlayLatest -Destination $mvpOverlay -Force

$mergeEraPresets = Join-Path $root "scripts\merge_logos_chronology_era_presets_v1.py"
Write-Host "[logos-chrono-bundle] (2b) merge era presets -> qa_presets JSON"
& py $mergeEraPresets
if ($LASTEXITCODE -ne 0) { throw "merge_logos_chronology_era_presets_v1.py failed: $LASTEXITCODE" }

$reasoningPathPy = Join-Path $root "scripts\compute_logos_reasoning_path_v1.py"
Write-Host "[logos-chrono-bundle] (2c) attach reasoning_path_v1 -> qa_presets (v4 visual path)"
& py $reasoningPathPy
if ($LASTEXITCODE -ne 0) { throw "compute_logos_reasoning_path_v1.py failed: $LASTEXITCODE" }

Write-Host "[logos-chrono-bundle] (3/4) deploy_showroom_static (oracle v3/v4 + overlay)"
& powershell -NoProfile -ExecutionPolicy Bypass -File $deploy -WorkspaceRoot $root
if ($LASTEXITCODE -ne 0) { throw "deploy_showroom_static.ps1 failed: $LASTEXITCODE" }

if (-not $SkipVpsSync) {
    Write-Host "[logos-chrono-bundle] (4/4) VPS sync"
    $syncArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $sync, "-WorkspaceRoot", $root)
    if ($ApplyRecommendedNginx) { $syncArgs += "-ApplyRecommendedNginx" }
    & powershell @syncArgs
    if ($LASTEXITCODE -ne 0) { throw "sync_showroom_to_vps.ps1 failed: $LASTEXITCODE" }
} else {
    Write-Host "[logos-chrono-bundle] VPS sync skipped (-SkipVpsSync)"
}

Write-Host "[logos-chrono-bundle] Done. Local: $mvpOverlay"
