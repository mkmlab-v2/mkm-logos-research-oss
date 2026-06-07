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
#   public_showroom_logos_research_v1.html + showroom_logos_research_slice_v0.json (optional; [HYPO]/NON_GATING; build_showroom_logos_research_slice_v1.py, chain step 6/7)
#   public_showroom_meaning_topology_graph_v1.html + showroom_meaning_topology_graph_slice_v1.json (optional; bible_meaning_graph subgraph; chain step 7/7)
#   public_showroom_meaning_topology_qa_v2.html + showroom_meaning_topology_qa_presets_v1.json (optional; Q&A studio + ECharts highlight; build_showroom_meaning_topology_qa_presets_v1.py)
#   public_showroom_logos_oracle_v3.html + v4 (visual path) + v5 (enterprise) + v6 (commercial) + showroom_logos_chronology_overlay_v1.json
#   public_showroom_probabilistic_saju_v1.html + showroom_saju_hour_bundle_demo_v1.json  (see scripts/run_saju_hour_candidate_bundle_v1.py)
#   public_showroom_lens_audio_thin_slice_v1.html + jemaai_lens_audio_playback_lut_v1_latest.json + showroom_lens_audio_thin_slice_v1.json (build_showroom_lens_audio_observability_v1.py / build_showroom_display_bundle.ps1)
#   audio/lens_btrack/v1/*.wav (optional; from reports/track_c_audio_hook_samples_v1 when present)

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
$macroHorizonArtifact = Join-Path $wsRoot "docs\final\artifacts\showroom_macro_horizon_2030_slice_v1_latest.json"
$savingNewsPanelArtifact = Join-Path $wsRoot "docs\final\artifacts\saving_the_news_matrix_panel_slice_v1_latest.json"
$savingNewsTopologyArtifact = Join-Path $wsRoot "docs\final\artifacts\saving_the_news_showroom_topology_slice_v1_latest.json"
$lensAudioLutArtifact = Join-Path $wsRoot "docs\final\artifacts\jemaai_lens_audio_playback_lut_v1_latest.json"
$lensAudioLutExample = Join-Path $wsRoot "docs\final\artifacts\jemaai_lens_audio_playback_lut_v1.example.json"
$lensVideoLutArtifact = Join-Path $wsRoot "docs\final\artifacts\jemaai_lens_video_playback_lut_v1_latest.json"
$lensVideoLutExample = Join-Path $wsRoot "docs\final\artifacts\jemaai_lens_video_playback_lut_v1.example.json"
$lensAudioHookDir = Join-Path $wsRoot "reports\track_c_audio_hook_samples_v1"
$lensVideoHookDir = Join-Path $wsRoot "reports\track_c_video_hook_samples_v1"
$files = @(
    @{ Name = "public_showroom_poll.html"; Src = Join-Path $mvp "public_showroom_poll.html" },
    @{ Name = "public_showroom_board_minimal.html"; Src = Join-Path $mvp "public_showroom_board_minimal.html" },
    @{ Name = "public_showroom_topology_radar_v1.html"; Src = Join-Path $mvp "public_showroom_topology_radar_v1.html" },
    @{ Name = "showroom_public_bundle_v1.json"; Src = Join-Path $mvp "showroom_public_bundle_v1.json" },
    @{ Name = "showroom_topology_radar_snapshot_v1_latest.json"; Src = $topologyArtifact; Optional = $true },
    @{ Name = "showroom_macro_horizon_2030_slice_v1_latest.json"; Src = $macroHorizonArtifact; Optional = $true },
    @{ Name = "public_showroom_trust_visualization_v0.html"; Src = Join-Path $mvp "public_showroom_trust_visualization_v0.html" },
    @{ Name = "showroom_trust_visualization_slice_v0.json"; Src = Join-Path $mvp "showroom_trust_visualization_slice_v0.json"; Optional = $true },
    @{ Name = "public_showroom_logos_research_v1.html"; Src = Join-Path $mvp "public_showroom_logos_research_v1.html" },
    @{ Name = "showroom_logos_research_slice_v0.json"; Src = Join-Path $mvp "showroom_logos_research_slice_v0.json"; Optional = $true },
    @{ Name = "public_showroom_meaning_topology_graph_v1.html"; Src = Join-Path $mvp "public_showroom_meaning_topology_graph_v1.html" },
    @{ Name = "showroom_meaning_topology_graph_slice_v1.json"; Src = Join-Path $mvp "showroom_meaning_topology_graph_slice_v1.json"; Optional = $true },
    @{ Name = "public_showroom_meaning_topology_qa_v2.html"; Src = Join-Path $mvp "public_showroom_meaning_topology_qa_v2.html" },
    @{ Name = "showroom_meaning_topology_qa_presets_v1.json"; Src = Join-Path $mvp "showroom_meaning_topology_qa_presets_v1.json"; Optional = $true },
    @{ Name = "public_showroom_logos_oracle_v3.html"; Src = Join-Path $mvp "public_showroom_logos_oracle_v3.html"; Optional = $true },
    @{ Name = "public_showroom_logos_oracle_v4.html"; Src = Join-Path $mvp "public_showroom_logos_oracle_v4.html"; Optional = $true },
    @{ Name = "public_showroom_logos_oracle_v5.html"; Src = Join-Path $mvp "public_showroom_logos_oracle_v5.html"; Optional = $true },
    @{ Name = "public_showroom_logos_oracle_v6.html"; Src = Join-Path $mvp "public_showroom_logos_oracle_v6.html"; Optional = $true },
    @{ Name = "showroom_logos_chronology_overlay_v1.json"; Src = Join-Path $mvp "showroom_logos_chronology_overlay_v1.json"; Optional = $true },
    @{ Name = "showroom_logos_chronology_dynamic_map_v1.json"; Src = Join-Path $mvp "showroom_logos_chronology_dynamic_map_v1.json"; Optional = $true },
    @{ Name = "showroom_logos_graph_wire_rag_poc_v1.json"; Src = Join-Path $mvp "showroom_logos_graph_wire_rag_poc_v1.json"; Optional = $true },
    @{ Name = "public_showroom_probabilistic_saju_v1.html"; Src = Join-Path $mvp "public_showroom_probabilistic_saju_v1.html" },
    @{ Name = "showroom_saju_hour_bundle_demo_v1.json"; Src = Join-Path $mvp "showroom_saju_hour_bundle_demo_v1.json" },
    @{ Name = "public_showroom_mkm_inter_agent_wire_v3.html"; Src = Join-Path $mvp "public_showroom_mkm_inter_agent_wire_v3.html"; Optional = $true },
    @{ Name = "public_showroom_saving_the_news_matrix_v1.html"; Src = Join-Path $mvp "public_showroom_saving_the_news_matrix_v1.html"; Optional = $true },
    @{ Name = "saving_the_news_matrix_panel_slice_v1_latest.json"; Src = $savingNewsPanelArtifact; Optional = $true },
    @{ Name = "saving_the_news_showroom_topology_slice_v1_latest.json"; Src = $savingNewsTopologyArtifact; Optional = $true },
    @{ Name = "public_showroom_lens_audio_thin_slice_v1.html"; Src = Join-Path $mvp "public_showroom_lens_audio_thin_slice_v1.html"; Optional = $true },
    @{ Name = "public_showroom_lens_media_thin_slice_v1.html"; Src = Join-Path $mvp "public_showroom_lens_media_thin_slice_v1.html"; Optional = $true },
    @{ Name = "showroom_lens_audio_thin_slice_v1.json"; Src = Join-Path $mvp "showroom_lens_audio_thin_slice_v1.json"; Optional = $true },
    @{ Name = "showroom_lens_media_thin_slice_v1.json"; Src = Join-Path $mvp "showroom_lens_media_thin_slice_v1.json"; Optional = $true },
    @{ Name = "jemaai_lens_audio_playback_lut_v1_latest.json"; Src = $lensAudioLutArtifact; Optional = $true },
    @{ Name = "jemaai_lens_audio_playback_lut_v1.example.json"; Src = $lensAudioLutExample; Optional = $true },
    @{ Name = "jemaai_lens_video_playback_lut_v1_latest.json"; Src = $lensVideoLutArtifact; Optional = $true },
    @{ Name = "jemaai_lens_video_playback_lut_v1.example.json"; Src = $lensVideoLutExample; Optional = $true }
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

# Lens audio static WAV staging (LUT filenames under audio/lens_btrack/v1/)
$audioLutMap = @(
    @{ Src = "dynamic_bgm_hp020_pass_v1.wav"; Dest = "hp020_soyang_idle_v1.wav" },
    @{ Src = "dynamic_bgm_hp050_pass_v1.wav"; Dest = "hp050_soyang_idle_v1.wav" },
    @{ Src = "dynamic_bgm_hp100_pass_v1.wav"; Dest = "hp100_soyang_defend_v1.wav" }
)
$audioDestDir = Join-Path $destRoot "audio\lens_btrack\v1"
if (Test-Path -LiteralPath $lensAudioHookDir) {
    $anyAudio = $false
    foreach ($m in $audioLutMap) {
        $srcWav = Join-Path $lensAudioHookDir $m.Src
        if (-not (Test-Path -LiteralPath $srcWav)) { continue }
        $anyAudio = $true
        if (-not $WhatIf -and -not (Test-Path -LiteralPath $audioDestDir)) {
            New-Item -ItemType Directory -Path $audioDestDir -Force | Out-Null
        }
        $dstWav = Join-Path $audioDestDir $m.Dest
        if ($WhatIf) {
            Write-Host "[deploy-showroom] WHATIF: copy $srcWav -> $dstWav"
        } else {
            Copy-Item -LiteralPath $srcWav -Destination $dstWav -Force
            Write-Host "[deploy-showroom] OK: $dstWav"
        }
    }
    if (-not $anyAudio) {
        Write-Warning "[deploy-showroom] optional lens audio WAV sources missing under $lensAudioHookDir"
    }
} else {
    Write-Warning "[deploy-showroom] optional lens audio hook dir missing: $lensAudioHookDir"
}

$videoDestDir = Join-Path $destRoot "video\lens_btrack\v1"
if (Test-Path -LiteralPath $lensVideoHookDir) {
    $webms = Get-ChildItem -LiteralPath $lensVideoHookDir -Filter "*.webm" -File -ErrorAction SilentlyContinue
    if ($webms -and $webms.Count -gt 0) {
        if (-not $WhatIf -and -not (Test-Path -LiteralPath $videoDestDir)) {
            New-Item -ItemType Directory -Path $videoDestDir -Force | Out-Null
        }
        foreach ($w in $webms) {
            $dstWebm = Join-Path $videoDestDir $w.Name
            if ($WhatIf) {
                Write-Host "[deploy-showroom] WHATIF: copy $($w.FullName) -> $dstWebm"
            } else {
                Copy-Item -LiteralPath $w.FullName -Destination $dstWebm -Force
                Write-Host "[deploy-showroom] OK: $dstWebm"
            }
        }
    } else {
        Write-Warning "[deploy-showroom] optional lens video WEBM missing under $lensVideoHookDir (run build_lens_btrack_video_loops_v1.py)"
    }
} else {
    Write-Warning "[deploy-showroom] optional lens video hook dir missing: $lensVideoHookDir"
}

# Fallback LUT latest from example when builder has not emitted latest yet
$lutLatestDest = Join-Path $destRoot "jemaai_lens_audio_playback_lut_v1_latest.json"
if (-not (Test-Path -LiteralPath $lutLatestDest) -and (Test-Path -LiteralPath $lensAudioLutExample)) {
    if ($WhatIf) {
        Write-Host "[deploy-showroom] WHATIF: copy $lensAudioLutExample -> $lutLatestDest (fallback)"
    } else {
        Copy-Item -LiteralPath $lensAudioLutExample -Destination $lutLatestDest -Force
        Write-Host "[deploy-showroom] OK (fallback LUT): $lutLatestDest"
    }
}

$videoLutLatestDest = Join-Path $destRoot "jemaai_lens_video_playback_lut_v1_latest.json"
if (-not (Test-Path -LiteralPath $videoLutLatestDest) -and (Test-Path -LiteralPath $lensVideoLutExample)) {
    if ($WhatIf) {
        Write-Host "[deploy-showroom] WHATIF: copy $lensVideoLutExample -> $videoLutLatestDest (fallback)"
    } else {
        Copy-Item -LiteralPath $lensVideoLutExample -Destination $videoLutLatestDest -Force
        Write-Host "[deploy-showroom] OK (fallback video LUT): $videoLutLatestDest"
    }
}

Write-Host "[deploy-showroom] Done. On Linux nginx host: copy to /var/www/jemaai/ then run: nginx -t ; systemctl reload nginx (see nginx_snippets/jemaai_showroom_ui.conf)."
