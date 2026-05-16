# Copies showroom static assets into a local or UNC web root (e.g. before rsync/scp to jemaai.cloud).
# Does not configure nginx on the server — deploy paths only.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File deploy_showroom_static.ps1
#   powershell ... -WebRoot "D:\staging\jemaai"
# Env: JEMAAI_WEB_ROOT — used if -WebRoot omitted (Process then User scope).
#
# If neither -WebRoot nor JEMAAI_WEB_ROOT is set, copies to this script's directory:
#   .showroom_staging/  (gitignored; same layout as nginx static root — open HTML from disk or rsync to VPS)
#
# Copies:
#   public_showroom_poll.html
#   public_showroom_board_minimal.html  (다크·미니멀 정적 보드; 동일 API 폴링)
#   public_showroom_topology_radar_v1.html  (Phase 2.1 Risk Topology Radar; snapshot + bundle + API)
#   showroom_public_bundle_v1.json  (from jemaai-cloud-mvp; run scripts/build_showroom_track_c_bundle_chain_v1.ps1 or build_showroom_display_bundle.ps1 first)
#   showroom_topology_radar_snapshot_v1_latest.json  (optional; from docs/final/artifacts after topology emit chain step)
#   public_showroom_trust_visualization_v0.html + showroom_trust_visualization_slice_v0.json (optional; from build_showroom_trust_visualization_slice_v1.py, also invoked at end of build_showroom_track_c_bundle_chain_v1.ps1)
#   public_showroom_logos_research_v1.html + showroom_logos_research_slice_v0.json (optional; [HYPO]/NON_GATING; build_showroom_logos_research_slice_v1.py, chain step 6/6)
#   public_showroom_probabilistic_saju_v1.html + showroom_saju_hour_bundle_demo_v1.json  (see scripts/run_saju_hour_candidate_bundle_v1.py)

param(
    [string]$WebRoot = "",
    [string]$WorkspaceRoot = "",
    [switch]$WhatIf,
    [switch]$NoDefaultStaging
)

$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$mvp = Join-Path $here "jemaai-cloud-mvp"
$defaultStaging = Join-Path $here ".showroom_staging"
$wsRoot = if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    (Resolve-Path (Join-Path $here "..\..\..\..")).Path
} else {
    (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}
$topologyArtifact = Join-Path $wsRoot "docs\final\artifacts\showroom_topology_radar_snapshot_v1_latest.json"
$files = @(
    @{ Name = "public_showroom_poll.html"; Src = Join-Path $mvp "public_showroom_poll.html" },
    @{ Name = "public_showroom_board_minimal.html"; Src = Join-Path $mvp "public_showroom_board_minimal.html" },
    @{ Name = "public_showroom_topology_radar_v1.html"; Src = Join-Path $mvp "public_showroom_topology_radar_v1.html" },
    @{ Name = "showroom_public_bundle_v1.json"; Src = Join-Path $mvp "showroom_public_bundle_v1.json" },
    @{ Name = "showroom_topology_radar_snapshot_v1_latest.json"; Src = $topologyArtifact; Optional = $true },
    @{ Name = "public_showroom_trust_visualization_v0.html"; Src = Join-Path $mvp "public_showroom_trust_visualization_v0.html" },
    @{ Name = "showroom_trust_visualization_slice_v0.json"; Src = Join-Path $mvp "showroom_trust_visualization_slice_v0.json"; Optional = $true },
    @{ Name = "public_showroom_logos_research_v1.html"; Src = Join-Path $mvp "public_showroom_logos_research_v1.html" },
    @{ Name = "showroom_logos_research_slice_v0.json"; Src = Join-Path $mvp "showroom_logos_research_slice_v0.json"; Optional = $true },
    @{ Name = "public_showroom_probabilistic_saju_v1.html"; Src = Join-Path $mvp "public_showroom_probabilistic_saju_v1.html" },
    @{ Name = "showroom_saju_hour_bundle_demo_v1.json"; Src = Join-Path $mvp "showroom_saju_hour_bundle_demo_v1.json" }
)

$destRoot = $WebRoot
if ([string]::IsNullOrWhiteSpace($destRoot)) {
    $destRoot = [Environment]::GetEnvironmentVariable("JEMAAI_WEB_ROOT", "Process")
}
if ([string]::IsNullOrWhiteSpace($destRoot)) {
    $destRoot = [Environment]::GetEnvironmentVariable("JEMAAI_WEB_ROOT", "User")
}

if ([string]::IsNullOrWhiteSpace($destRoot)) {
    if ($NoDefaultStaging) {
        Write-Host "[deploy-showroom] SKIP: set -WebRoot, JEMAAI_WEB_ROOT, or omit -NoDefaultStaging to use .showroom_staging."
        exit 0
    }
    $destRoot = $defaultStaging
    if (-not (Test-Path -LiteralPath $destRoot)) {
        New-Item -ItemType Directory -Path $destRoot -Force | Out-Null
    }
    Write-Host "[deploy-showroom] JEMAAI_WEB_ROOT unset; using default staging: $destRoot"
}

if (-not (Test-Path -LiteralPath $destRoot)) {
    throw "[deploy-showroom] destination does not exist: $destRoot"
}

foreach ($f in $files) {
    if (-not (Test-Path -LiteralPath $f.Src)) {
        if ($f.Optional) {
            Write-Warning "[deploy-showroom] optional source missing (skipped): $($f.Name)"
        } else {
            Write-Warning "[deploy-showroom] missing source: $($f.Src) — run build_showroom_display_bundle.ps1"
        }
        continue
    }
    $out = Join-Path $destRoot $f.Name
    if ($WhatIf) {
        Write-Host "[deploy-showroom] WHATIF: copy $($f.Src) -> $out"
    } else {
        Copy-Item -LiteralPath $f.Src -Destination $out -Force
        Write-Host "[deploy-showroom] OK: $out"
    }
}

Write-Host "[deploy-showroom] Done. On Linux nginx host: copy to /var/www/jemaai/ then run: nginx -t ; systemctl reload nginx (see nginx_snippets/jemaai_showroom_ui.conf)."
