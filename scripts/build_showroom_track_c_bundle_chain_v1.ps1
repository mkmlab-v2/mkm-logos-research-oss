# Track C public showroom: freshness sidecar -> topology radar snapshot -> showroom bundle -> validate -> trust viz thin slice (Fact-Lock).
# Does not scp/VPS — use scripts/sync_showroom_to_vps.ps1 -RefreshStaging after this, or deploy_showroom_static.ps1.
#
# Usage (repo root):
#   pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/build_showroom_track_c_bundle_chain_v1.ps1
#   pwsh ... -SkipFreshnessSidecar   # only rebuild showroom JSON from current disk inputs
#   pwsh ... -SkipTopologyRadarSnapshot
#   pwsh ... -SkipMacroHorizon2030Slice
#   pwsh ... -TopologyRadarSnapshotStrict   # fail if no graph/sidecar artifacts (no stub ref)
#   pwsh ... -SkipValidate          # skip validate_showroom_public_bundle.py
#   pwsh ... -SkipLogosResearchSlice  # skip build_showroom_logos_research_slice_v1.py
#   pwsh ... -SkipMeaningTopologyGraphSlice  # skip build_showroom_meaning_topology_graph_slice_v1.py
#   pwsh ... -SkipLogosIntegrityOrbSlice  # skip build_showroom_logos_integrity_orb_slice_v1.py
#   pwsh ... -SkipJobReadingPackSlice  # skip build_showroom_logos_job_reading_pack_slice_v1.py

param(
    [string]$WorkspaceRoot = "",
    [switch]$SkipFreshnessSidecar,
    [switch]$SkipTopologyRadarSnapshot,
    [switch]$TopologyRadarSnapshotStrict,
    [switch]$SkipMacroHorizon2030Slice,
    [switch]$SkipValidate,
    [switch]$SkipLogosResearchSlice,
    [switch]$SkipMeaningTopologyGraphSlice,
    [switch]$SkipLogosIntegrityOrbSlice,
    [switch]$SkipJobReadingPackSlice
)

$ErrorActionPreference = "Stop"
$root = if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    $WorkspaceRoot
}
Set-Location -LiteralPath $root

$py = "py"
if (-not (Get-Command $py -ErrorAction SilentlyContinue)) {
    $py = "python"
}

Write-Host "=== build_showroom_track_c_bundle_chain_v1 (WorkspaceRoot=$root) ===" -ForegroundColor Cyan

if (-not $SkipFreshnessSidecar) {
    Write-Host "[chain] (1/6) logos_track_c_freshness_sidecar" -ForegroundColor Cyan
    & $py (Join-Path $root "scripts\build_logos_track_c_freshness_sidecar_v1.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "build_logos_track_c_freshness_sidecar_v1.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[chain] (1/6) SKIP freshness sidecar" -ForegroundColor Yellow
}

if (-not $SkipTopologyRadarSnapshot) {
    Write-Host "[chain] (2/6) showroom_topology_radar_snapshot_v1 emit" -ForegroundColor Cyan
    $snapArgs = @(
        (Join-Path $root "scripts\build_showroom_topology_radar_snapshot_v1.py"),
        "--workspace-root",
        $root
    )
    if (-not $TopologyRadarSnapshotStrict) {
        $snapArgs += "--allow-stub-ref"
    }
    & $py @snapArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "build_showroom_topology_radar_snapshot_v1.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[chain] (2/7) SKIP topology radar snapshot" -ForegroundColor Yellow
}

if (-not $SkipMacroHorizon2030Slice) {
    Write-Host "[chain] (3/7) showroom_macro_horizon_2030_slice_v1 emit" -ForegroundColor Cyan
    & $py (Join-Path $root "scripts\build_showroom_macro_horizon_2030_slice_v1.py") --workspace-root $root
    if ($LASTEXITCODE -ne 0) {
        Write-Error "build_showroom_macro_horizon_2030_slice_v1.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[chain] (3/7) SKIP macro horizon 2030 slice" -ForegroundColor Yellow
}

$buildPs1 = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\build_showroom_display_bundle.ps1"
Write-Host "[chain] (4/7) build_showroom_display_bundle (+ lens_audio_observability_v1)" -ForegroundColor Cyan
$psExe = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell.exe" }
& $psExe -NoProfile -ExecutionPolicy Bypass -File $buildPs1 -WorkspaceRoot $root
if ($LASTEXITCODE -ne 0) {
    Write-Error "build_showroom_display_bundle.ps1 failed: $LASTEXITCODE"
    exit $LASTEXITCODE
}

$bundleOut = Join-Path $root "docs\final\artifacts\showroom_public_bundle_v1.json"
if (-not $SkipValidate) {
    Write-Host "[chain] (5/7) validate_showroom_public_bundle" -ForegroundColor Cyan
    & $py (Join-Path $root "scripts\validate_showroom_public_bundle.py") $bundleOut
    if ($LASTEXITCODE -ne 0) {
        Write-Error "validate_showroom_public_bundle.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[chain] (5/7) SKIP validate" -ForegroundColor Yellow
}

Write-Host "[chain] (6/7) showroom trust visualization thin slice (dashboard -> JSON)" -ForegroundColor Cyan
& $py (Join-Path $root "scripts\build_showroom_trust_visualization_slice_v1.py")
if ($LASTEXITCODE -ne 0) {
    Write-Error "build_showroom_trust_visualization_slice_v1.py failed: $LASTEXITCODE"
    exit $LASTEXITCODE
}

if (-not $SkipLogosResearchSlice) {
    Write-Host "[chain] (6/7) showroom Logos research thin slice (theme DB -> JSON)" -ForegroundColor Cyan
    & $py (Join-Path $root "scripts\build_showroom_logos_research_slice_v1.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "build_showroom_logos_research_slice_v1.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[chain] (6/7) SKIP Logos research slice" -ForegroundColor Yellow
}

if (-not $SkipMeaningTopologyGraphSlice) {
    Write-Host "[chain] (7/8) showroom meaning topology graph slice (graph JSONL -> capped subgraph + Job spine)" -ForegroundColor Cyan
    & $py (Join-Path $root "scripts\run_showroom_job_topology_wiring_chain_v1.py") --skip-pytest
    if ($LASTEXITCODE -ne 0) {
        Write-Error "run_showroom_job_topology_wiring_chain_v1.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[chain] (7-8/9) SKIP meaning topology graph slice + Q&A presets" -ForegroundColor Yellow
}

if (-not $SkipLogosIntegrityOrbSlice) {
    Write-Host "[chain] (9/9) showroom Logos Integrity Orb slice (ENTRY_13/16 -> JSON)" -ForegroundColor Cyan
    & $py (Join-Path $root "scripts\build_showroom_logos_integrity_orb_slice_v1.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "build_showroom_logos_integrity_orb_slice_v1.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[chain] (9/10) SKIP Logos Integrity Orb slice" -ForegroundColor Yellow
}

if (-not $SkipJobReadingPackSlice) {
    Write-Host "[chain] (10/10) showroom Job reading-pack slice (topology 3-pack -> public JSON)" -ForegroundColor Cyan
    & $py (Join-Path $root "scripts\run_logos_job_reading_pack_verify_chain_v1.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "run_logos_job_reading_pack_verify_chain_v1.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
    & $py (Join-Path $root "scripts\build_showroom_logos_job_reading_pack_slice_v1.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "build_showroom_logos_job_reading_pack_slice_v1.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
    Write-Host "[chain] (10b/10) refresh Q&A presets (merge Job reading-pack presets)" -ForegroundColor Cyan
    & $py (Join-Path $root "scripts\build_showroom_meaning_topology_qa_presets_v1.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "build_showroom_meaning_topology_qa_presets_v1.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
    Write-Host "[chain] (10b2/10) GraphRAG router -> Q&A presets sidecar" -ForegroundColor Cyan
    & $py (Join-Path $root "scripts\export_showroom_qa_router_paths_v1.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "export_showroom_qa_router_paths_v1.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
    Write-Host "[chain] (10c/10) refresh showroom public URL SSOT (Logos demo spine)" -ForegroundColor Cyan
    & $py (Join-Path $root "scripts\build_jemaai_showroom_public_urls_v1.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "build_jemaai_showroom_public_urls_v1.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[chain] (10/10) SKIP Job reading-pack slice" -ForegroundColor Yellow
}

Write-Host "[chain] OK -> $bundleOut (+ trust viz + logos + meaning graph + integrity orb + job reading pack under jemaai-cloud-mvp/)" -ForegroundColor Green
exit 0
