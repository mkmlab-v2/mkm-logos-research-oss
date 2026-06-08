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
    @{ Name = "public_showroom_lens_audio_ab_smoke_v1.html"; Src = Join-Path $mvp "public_showroom_lens_audio_ab_smoke_v1.html"; Optional = $true },
    @{ Name = "public_showroom_lens_stable_audio_matrix_v1.html"; Src = Join-Path $mvp "public_showroom_lens_stable_audio_matrix_v1.html"; Optional = $true },
    @{ Name = "showroom_lens_audio_thin_slice_v1.json"; Src = Join-Path $mvp "showroom_lens_audio_thin_slice_v1.json"; Optional = $true },
    @{ Name = "showroom_lens_media_thin_slice_v1.json"; Src = Join-Path $mvp "showroom_lens_media_thin_slice_v1.json"; Optional = $true },
    @{ Name = "showroom_lens_audio_ab_smoke_v1.json"; Src = Join-Path $mvp "showroom_lens_audio_ab_smoke_v1.json"; Optional = $true },
    @{ Name = "showroom_lens_stable_audio_matrix_v1.json"; Src = Join-Path $mvp "showroom_lens_stable_audio_matrix_v1.json"; Optional = $true },
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
$audioDestDir = Join-Path $destRoot "audio\lens_btrack\v1"
$audioLutForDeploy = $lensAudioLutArtifact
if (-not (Test-Path -LiteralPath $audioLutForDeploy)) {
    $audioLutForDeploy = $lensAudioLutExample
}
if (Test-Path -LiteralPath $audioLutForDeploy) {
    try {
        $lutDoc = Get-Content -LiteralPath $audioLutForDeploy -Raw -Encoding utf8 | ConvertFrom-Json
        $entries = $lutDoc.entries
        if ($entries) {
            $anyAudio = $false
            foreach ($prop in $entries.PSObject.Properties) {
                $destName = [string]$prop.Value.file
                if ([string]::IsNullOrWhiteSpace($destName)) { continue }
                $srcWav = Join-Path $lensAudioHookDir $destName
                if (-not (Test-Path -LiteralPath $srcWav)) {
                    Write-Warning "[deploy-showroom] optional lens audio WAV missing: $destName"
                    continue
                }
                $anyAudio = $true
                if (-not $WhatIf -and -not (Test-Path -LiteralPath $audioDestDir)) {
                    New-Item -ItemType Directory -Path $audioDestDir -Force | Out-Null
                }
                $dstWav = Join-Path $audioDestDir $destName
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
        }
    } catch {
        Write-Warning "[deploy-showroom] lens audio LUT parse failed: $audioLutForDeploy — $_"
    }
} elseif (Test-Path -LiteralPath $lensAudioHookDir) {
    Write-Warning "[deploy-showroom] lens audio LUT missing; skipped WAV staging"
} else {
    Write-Warning "[deploy-showroom] optional lens audio hook dir missing: $lensAudioHookDir"
}

$lensStableAudioDir = Join-Path $destRoot "audio\lens_btrack\stable_audio_open\v1"
$lensStableAudioSrc = Join-Path $defaultStaging "audio\lens_btrack\stable_audio_open\v1"
if (Test-Path -LiteralPath $lensStableAudioSrc) {
    $stableSrcResolved = (Resolve-Path -LiteralPath $lensStableAudioSrc).Path
    $stableDestResolved = (Resolve-Path -LiteralPath $lensStableAudioDir -ErrorAction SilentlyContinue)
    if ($stableDestResolved -and $stableSrcResolved -eq $stableDestResolved.Path) {
        Write-Host "[deploy-showroom] lens stable audio WAV already in dest (skip copy)"
    } else {
        $stableWavs = @(Get-ChildItem -LiteralPath $lensStableAudioSrc -Filter "*.wav" -File -ErrorAction SilentlyContinue)
        if ($stableWavs.Count -gt 0) {
            if (-not $WhatIf -and -not (Test-Path -LiteralPath $lensStableAudioDir)) {
                New-Item -ItemType Directory -Path $lensStableAudioDir -Force | Out-Null
            }
            foreach ($w in $stableWavs) {
                $dst = Join-Path $lensStableAudioDir $w.Name
                if ($WhatIf) {
                    Write-Host "[deploy-showroom] WHATIF: copy $($w.FullName) -> $dst"
                } else {
                    Copy-Item -LiteralPath $w.FullName -Destination $dst -Force
                    Write-Host "[deploy-showroom] OK: $dst"
                }
            }
        }
    }
}

$lensAbSmokeDir = Join-Path $destRoot "audio\lens_btrack\ab_smoke\v1"
$lensAbSmokeSrc = Join-Path $defaultStaging "audio\lens_btrack\ab_smoke\v1"
if (Test-Path -LiteralPath $lensAbSmokeSrc) {
    $abSrcResolved = (Resolve-Path -LiteralPath $lensAbSmokeSrc).Path
    $abDestResolved = (Resolve-Path -LiteralPath $lensAbSmokeDir -ErrorAction SilentlyContinue)
    if ($abDestResolved -and $abSrcResolved -eq $abDestResolved.Path) {
        Write-Host "[deploy-showroom] lens AB smoke WAV already in dest (skip copy)"
    } else {
        $abWavs = @(Get-ChildItem -LiteralPath $lensAbSmokeSrc -Filter "*.wav" -File -ErrorAction SilentlyContinue)
        if ($abWavs.Count -gt 0) {
            if (-not $WhatIf -and -not (Test-Path -LiteralPath $lensAbSmokeDir)) {
                New-Item -ItemType Directory -Path $lensAbSmokeDir -Force | Out-Null
            }
            foreach ($w in $abWavs) {
                $dst = Join-Path $lensAbSmokeDir $w.Name
                if ($WhatIf) {
                    Write-Host "[deploy-showroom] WHATIF: copy $($w.FullName) -> $dst"
                } else {
                    Copy-Item -LiteralPath $w.FullName -Destination $dst -Force
                    Write-Host "[deploy-showroom] OK: $dst"
                }
            }
        }
    }
}

$videoDestDir = Join-Path $destRoot "video\lens_btrack\v1"
$videoLutForDeploy = $lensVideoLutArtifact
if (-not (Test-Path -LiteralPath $videoLutForDeploy)) {
    $videoLutForDeploy = $lensVideoLutExample
}
if (Test-Path -LiteralPath $videoLutForDeploy) {
    try {
        $vLutDoc = Get-Content -LiteralPath $videoLutForDeploy -Raw -Encoding utf8 | ConvertFrom-Json
        $vEntries = $vLutDoc.entries
        $allowedVideo = @{}
        if ($vEntries) {
            $anyVideo = $false
            foreach ($prop in $vEntries.PSObject.Properties) {
                $destName = [string]$prop.Value.file
                if ([string]::IsNullOrWhiteSpace($destName)) { continue }
                $allowedVideo[$destName] = $true
                $srcWebm = Join-Path $lensVideoHookDir $destName
                if (-not (Test-Path -LiteralPath $srcWebm)) {
                    Write-Warning "[deploy-showroom] optional lens video WEBM missing: $destName"
                } else {
                    $anyVideo = $true
                    if (-not $WhatIf -and -not (Test-Path -LiteralPath $videoDestDir)) {
                        New-Item -ItemType Directory -Path $videoDestDir -Force | Out-Null
                    }
                    $dstWebm = Join-Path $videoDestDir $destName
                    if ($WhatIf) {
                        Write-Host "[deploy-showroom] WHATIF: copy $srcWebm -> $dstWebm"
                    } else {
                        Copy-Item -LiteralPath $srcWebm -Destination $dstWebm -Force
                        Write-Host "[deploy-showroom] OK: $dstWebm"
                    }
                }
                $mp4Name = [string]$prop.Value.mp4_file
                if ([string]::IsNullOrWhiteSpace($mp4Name) -and $destName.ToLower().EndsWith(".webm")) {
                    $mp4Name = ($destName.Substring(0, $destName.Length - 5) + ".mp4")
                }
                if (-not [string]::IsNullOrWhiteSpace($mp4Name)) {
                    $allowedVideo[$mp4Name] = $true
                    $srcMp4 = Join-Path $lensVideoHookDir $mp4Name
                    if (Test-Path -LiteralPath $srcMp4) {
                        if (-not $WhatIf -and -not (Test-Path -LiteralPath $videoDestDir)) {
                            New-Item -ItemType Directory -Path $videoDestDir -Force | Out-Null
                        }
                        $anyVideo = $true
                        $dstMp4 = Join-Path $videoDestDir $mp4Name
                        if ($WhatIf) {
                            Write-Host "[deploy-showroom] WHATIF: copy $srcMp4 -> $dstMp4"
                        } else {
                            Copy-Item -LiteralPath $srcMp4 -Destination $dstMp4 -Force
                            Write-Host "[deploy-showroom] OK: $dstMp4"
                        }
                    } else {
                        Write-Warning "[deploy-showroom] optional lens video MP4 missing: $mp4Name"
                    }
                }
                $posterName = [string]$prop.Value.poster_file
                if ([string]::IsNullOrWhiteSpace($posterName) -and $destName.ToLower().EndsWith(".webm")) {
                    $posterName = ($destName.Substring(0, $destName.Length - 5) + "_poster.png")
                }
                if (-not [string]::IsNullOrWhiteSpace($posterName)) {
                    $allowedVideo[$posterName] = $true
                    $srcPoster = Join-Path $lensVideoHookDir $posterName
                    if (Test-Path -LiteralPath $srcPoster) {
                        if (-not $WhatIf -and -not (Test-Path -LiteralPath $videoDestDir)) {
                            New-Item -ItemType Directory -Path $videoDestDir -Force | Out-Null
                        }
                        $anyVideo = $true
                        $dstPoster = Join-Path $videoDestDir $posterName
                        if ($WhatIf) {
                            Write-Host "[deploy-showroom] WHATIF: copy $srcPoster -> $dstPoster"
                        } else {
                            Copy-Item -LiteralPath $srcPoster -Destination $dstPoster -Force
                            Write-Host "[deploy-showroom] OK: $dstPoster"
                        }
                    } else {
                        Write-Warning "[deploy-showroom] optional lens video poster missing: $posterName"
                    }
                }
            }
            if (-not $anyVideo) {
                Write-Warning "[deploy-showroom] optional lens video WEBM sources missing under $lensVideoHookDir"
            }
            if (-not $WhatIf -and (Test-Path -LiteralPath $videoDestDir)) {
                Get-ChildItem -LiteralPath $videoDestDir -File -ErrorAction SilentlyContinue |
                    Where-Object { $_.Extension -in @(".webm", ".mp4", ".png") } |
                    ForEach-Object {
                    if (-not $allowedVideo.ContainsKey($_.Name)) {
                        Remove-Item -LiteralPath $_.FullName -Force
                        Write-Host "[deploy-showroom] PRUNED orphan video: $($_.Name)"
                    }
                }
            }
        }
    } catch {
        Write-Warning "[deploy-showroom] lens video LUT parse failed: $videoLutForDeploy — $_"
    }
} elseif (Test-Path -LiteralPath $lensVideoHookDir) {
    Write-Warning "[deploy-showroom] lens video LUT missing; skipped WEBM staging"
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
