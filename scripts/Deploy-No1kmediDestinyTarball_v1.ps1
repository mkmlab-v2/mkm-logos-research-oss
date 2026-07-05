<#
.SYNOPSIS
  Deploy projects/no1kmedi to VPS PM2 path via tarball (when VPS git pull lags local bare).

.DESCRIPTION
  PM2 no1kmedi-com exec cwd: /opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi

  Recommended order (local):
    1. Commit + push monorepo to internal (scripts/push-internal.ps1) so VPS can ff-only pull scripts/data/schemas.
    2. Run this script (tarball overwrites projects/no1kmedi; monorepo root is synced via git pull on VPS).

  Sets on VPS .env.local (never shipped in tarball): MKM_WORKSPACE_ROOT, MKM_PYTHON,
  KM_PATIENT_CARE_BUNDLE_TRUST_SAME_ORIGIN, KM_CLINICIAN_PASTE_EXTRACT_LLM (before npm build).
  Clinician LLM keys + Pro allowlist: scripts\Sync-No1kmediClinicianOpsEnvToVps_v1.ps1
  Webhook env: scripts\Sync-CompressionPilotAuditWebhook_v1.ps1 -SyncVps

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Deploy-No1kmediDestinyTarball_v1.ps1
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Deploy-No1kmediDestinyTarball_v1.ps1 -SkipMonorepoSync -RunApiSmoke
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$SshIdentityFile = "",
    [string]$MonorepoRemote = "origin",
    [string]$MonorepoBranch = "main",
    [switch]$DryRun,
    [switch]$SkipLocalBuild,
    [switch]$SkipMonorepoSync,
    [switch]$SkipMonorepoPathsFromLocal,
    [switch]$RunApiSmoke
)

$ErrorActionPreference = "Stop"

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($v) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if ($v) { return $v.Trim() }
    return ""
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
if (-not $hostName) { $hostName = "vps-mkmlife" }
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$remote = "${user}@${hostName}"
$vpsDestinyRepo = "/opt/mkm-destiny-ai-41e38ec6"
$vpsDest = "$vpsDestinyRepo/projects/no1kmedi"
$vpsParent = "$vpsDestinyRepo/projects"
$src = Join-Path $WorkspaceRoot "projects\no1kmedi"

if (-not (Test-Path $src)) { throw "missing $src" }

$sshArgs = @()
if ($SshIdentityFile) { $sshArgs = @("-i", $SshIdentityFile) }
else {
    $extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
    if ($extra) { $sshArgs = $extra -split "\s+" | Where-Object { $_ } }
}

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$tarLocal = Join-Path $env:TEMP "no1kmedi-deploy-$stamp.tar.gz"
$tarRemote = "/tmp/no1kmedi-deploy-$stamp.tar.gz"

$monorepoRequiredPaths = @(
    "$vpsDestinyRepo/scripts/build_km_physician_cds_assist_envelope_v1.py",
    "$vpsDestinyRepo/scripts/lookup_dssbw_chunks_v1.py",
    "$vpsDestinyRepo/data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl",
    "$vpsDestinyRepo/scripts/build_patient_care_bundle_from_km_cds_chain_v1.py",
    "$vpsDestinyRepo/data/myeongni/myeongni_school_conflict_resolver_v1.json",
    "$vpsDestinyRepo/docs/final/artifacts/patient_care_bundle_slot_templates_ko_v1.json",
    "$vpsDestinyRepo/docs/final/schemas/km_physician_cds_assist_envelope_v1.schema.json"
)

if (-not $SkipMonorepoSync) {
    $pullCmd = (@"
cd $vpsDestinyRepo
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git fetch $MonorepoRemote $MonorepoBranch && git pull --ff-only $MonorepoRemote $MonorepoBranch || echo '[no1kmedi-tarball] WARN: git pull failed (will try local path sync)'
else
  echo '[no1kmedi-tarball] WARN: monorepo not a git checkout — skip pull'
fi
"@).Replace("`r`n", "`n").Replace("`r", "`n").TrimEnd() + "`n"

    Write-Host "[no1kmedi-tarball] VPS monorepo: git pull $MonorepoRemote/$MonorepoBranch (best-effort)" -ForegroundColor Cyan
    if (-not $DryRun) {
        & ssh @($sshArgs + @($remote, $pullCmd))
    }
}

if (-not $SkipMonorepoPathsFromLocal) {
    $localMono = $WorkspaceRoot
    $relFiles = @(
        "scripts/build_km_physician_cds_assist_envelope_v1.py",
        "scripts/lookup_dssbw_chunks_v1.py",
        "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl",
        "scripts/build_patient_care_bundle_from_km_cds_chain_v1.py",
        "scripts/encode_logos_studio_query_embedding_v1.py",
        "scripts/encode_logos_studio_query_graphrag_v1.py",
        "scripts/export_showroom_qa_router_paths_v1.py",
        "scripts/logos_studio_embedding_sidecar_v1.py",
        "scripts/logos_ann_lite_embedding_v1.py",
        "scripts/compute_logos_reasoning_path_v1.py",
        "scripts/logos_verse_ref_canonical_v1.py",
        "scripts/logos_gematria_lexicon_router_lib_v1.py",
        "scripts/assemble_patient_care_bundle_with_myeongni_v1.py",
        "scripts/build_myeongni_full_report_v1.py",
        "scripts/run_saju_global_birth_v1.py",
        "scripts/saju_birth_resolver_v1.py",
        "scripts/apply_patient_care_bundle_slot_templates_v1.py",
        "scripts/validate_patient_care_bundle_against_policy_v1.py",
        "scripts/render_patient_care_bundle_markdown_v1.py",
        "docs/final/schemas/km_physician_cds_assist_envelope_v1.schema.json",
        "docs/final/schemas/mkm_bianzheng_tri_layer_v1.schema.json",
        "docs/final/schemas/patient_care_bundle_v1.schema.json",
        "docs/final/artifacts/patient_care_bundle_slot_templates_ko_v1.json",
        "docs/final/artifacts/patient_care_bundle_generation_policy_v1.default.json",
        "docs/final/artifacts/clinic_constitution_survey_item_bank_v1.json",
        "tests/fixtures/patient_care_bundle_soap_stub_v1.example.json",
        "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json",
        "docs/final/artifacts/showroom_meaning_topology_qa_router_sidecar_v1_latest.json",
        "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json",
        "docs/final/artifacts/logos_studio_preset_taxonomy_v1_latest.json",
        "docs/final/artifacts/logos_studio_semantic_router_lexical_index_v1_latest.json",
        "docs/final/artifacts/logos_studio_semantic_router_embedding_index_v1_latest.json",
        "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json",
        "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl",
        "docs/final/artifacts/logos_studio_lemma_neighbor_index_v1_latest.json",
        "docs/final/artifacts/logos_studio_lemma_neighbor_index_v1_latest.pkl",
        "docs/final/artifacts/showroom_logos_isaiah_youtube_reading_pack_slice_v1_latest.json",
        "docs/final/artifacts/logos_graph_seed_chain_v1_latest.json",
        "docs/final/artifacts/lens_context_mesh_hop_index_logos_v1_latest.json",
        "docs/final/artifacts/showroom_era_insight_lattice_genesis_v1_latest.json",
        "docs/final/artifacts/logos_cross_ref_sample_shard_v1_latest.json",
        "docs/final/artifacts/bigset_studio_conflict_sidecar_v1_latest.json",
        "docs/final/artifacts/showroom_logos_job_reading_pack_slice_v1_latest.json",
        "docs/final/artifacts/showroom_logos_gen2_eve_reading_pack_slice_v1_latest.json",
        "docs/final/artifacts/showroom_logos_tsela_concordance_v1_latest.json",
        "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_job_reading_pack_slice_v1.json",
        "docs/final/artifacts/logos_studio_verse_citation_shard_v1_latest.json",
        "docs/final/artifacts/logos_studio_a4_synthesis_bundle_v1_latest.json",
        "docs/final/artifacts/logos_studio_graph_slice_ui_lite_v1_latest.json",
        "docs/final/artifacts/lens_context_mesh_hop_index_logos_ui_lite_v1_latest.json",
        "docs/final/artifacts/logos_studio_31k_bloom_secondary_fetch_v1_latest.json",
        "docs/final/artifacts/logos_studio_dynamic_subgraph_router_v1_latest.json",
        "docs/final/artifacts/logos_krv_versification_sidecar_v1_latest.json",
        "scripts/build_logos_studio_graph_slice_ui_lite_v1.py",
        "scripts/lens_context_mesh_v1.py",
        "scripts/merge_logos_studio_embed_router_sidecar_v1.py",
        "scripts/patch_logos_studio_graph_slice_router_verse_stubs_v1.py",
        "scripts/retrieve_logos_studio_conflict_context_v1.py",
        "scripts/logos_studio_query_topic_guard_v1.py",
        "scripts/synthesize_logos_studio_dynamic_answer_v1.py",
        "scripts/synthesize_logos_studio_gen2_azure_distill_v1.py",
        "scripts/synthesize_logos_studio_azure_distill_v1.py",
        "scripts/build_logos_tsela_concordance_v1.py",
        "scripts/build_logos_studio_lemma_neighbor_index_v1.py",
        "scripts/synthesize_logos_studio_lemma_bridge_answer_v1.py",
        "scripts/build_logos_studio_lemma_neighbor_index_v1.py",
        "scripts/logos_studio_bloom_secondary_fetch_lib_v1.py",
        "scripts/run_logos_subgraph_graphrag_router_v1.py",
        "scripts/run_logos_llm_distill_citation_lock_v1.py",
        "scripts/build_bigset_studio_conflict_sidecar_v1.py",
        "scripts/logos_studio_preset_graph_helpers_v1.py",
        "scripts/integrated_wellness_solution_v2_core.py",
        "scripts/resolve_integrated_wellness_solution_v2.py",
        "scripts/render_integrated_wellness_solution_v2.py",
        "scripts/run_integrated_wellness_solution_v2_chain_v1.py",
        "scripts/publish_integrated_wellness_solution_v2_exports_v1.py",
        "scripts/build_integrated_wellness_seed_from_consult_v1.py",
        "scripts/adapt_integrated_wellness_personadiary_export_v1.py",
        "docs/final/schemas/integrated_wellness_solution_v2.schema.json",
        "docs/final/artifacts/a_code_wellness_archetype_lexicon_v1.json",
        "docs/final/artifacts/clinician_ijeoma_eight_channel_weight_contract_v1.json",
        "docs/final/artifacts/fixtures/integrated_wellness_solution_v2_minor_soeum_abdomen_seed.example.json",
        "scripts/check_public_facing_copy_gate_v1.py",
        "docs/final/MKM_PUBLIC_IDENTITY_CONSTITUTION_V1.md",
        "docs/final/artifacts/JEMAAI_TECH_PROMO_SAFE_COPY_V1.md"
    )
    Write-Host "[no1kmedi-tarball] scp monorepo CDS/bundle/IWS paths from local" -ForegroundColor Cyan
    if (-not $DryRun) {
        & ssh @($sshArgs + @($remote, "mkdir -p $vpsDestinyRepo/scripts $vpsDestinyRepo/docs/final/schemas $vpsDestinyRepo/docs/final/artifacts $vpsDestinyRepo/docs/final/artifacts/fixtures $vpsDestinyRepo/tests/fixtures $vpsDestinyRepo/data/myeongni $vpsDestinyRepo/data/corpus/ijeoma/_inventory"))
        foreach ($rel in $relFiles) {
            $localPath = Join-Path $localMono $rel
            if (-not (Test-Path $localPath)) { throw "missing local monorepo file: $localPath" }
            $remoteDir = "$vpsDestinyRepo/" + ($rel -replace "/[^/]+$", "" -replace "\\", "/")
            & scp @($sshArgs + @($localPath, "${remote}:${remoteDir}/"))
            if ($LASTEXITCODE -ne 0) { throw "scp failed: $rel" }
        }
        $myeongniLocal = Join-Path $localMono "data\myeongni"
        if (Test-Path $myeongniLocal) {
            & scp @($sshArgs + @("-r", $myeongniLocal, "${remote}:$vpsDestinyRepo/data/"))
            if ($LASTEXITCODE -ne 0) { throw "scp data/myeongni failed" }
        }
    }
}

if (-not $SkipMonorepoSync -or -not $SkipMonorepoPathsFromLocal) {
    $pathList = ($monorepoRequiredPaths | ForEach-Object { "'$_'" }) -join " "
    $gateCmd = (@"
set -e
for f in $pathList; do
  test -f "`$f" || { echo "missing: `$f"; exit 1; }
done
echo '[no1kmedi-tarball] monorepo path gate OK'
"@).Replace("`r`n", "`n").Replace("`r", "`n").TrimEnd() + "`n"
    Write-Host "[no1kmedi-tarball] monorepo path gate" -ForegroundColor Cyan
    if (-not $DryRun) {
        & ssh @($sshArgs + @($remote, $gateCmd))
        if ($LASTEXITCODE -ne 0) { throw "monorepo path gate failed on VPS" }
    }
}

if (-not $SkipLocalBuild) {
    Write-Host "[no1kmedi-tarball] local npm run build" -ForegroundColor Cyan
    Push-Location $src
    try {
        $env:NEXT_PUBLIC_UNIVERSE_HUB_MKMLIFE_EMBED = "1"
        & npm run build
        if ($LASTEXITCODE -ne 0) { throw "local build failed exit $LASTEXITCODE" }
    } finally { Pop-Location }
}

Write-Host "[no1kmedi-tarball] archive (excludes node_modules/.next/.env.local)" -ForegroundColor Cyan
if (Test-Path $tarLocal) { Remove-Item $tarLocal -Force }
& tar -czf $tarLocal -C (Join-Path $WorkspaceRoot "projects") --exclude=node_modules --exclude=.next --exclude=.env.local no1kmedi
if ($LASTEXITCODE -ne 0) { throw "tar failed" }

if ($DryRun) {
    Write-Host "DRY-RUN: scp $tarLocal -> ${remote}:$tarRemote"
    Write-Host "DRY-RUN: ssh extract -> $vpsDest ; npm ci ; npm run build ; pm2 restart no1kmedi-com"
    exit 0
}

Write-Host "[no1kmedi-tarball] scp" -ForegroundColor Cyan
& scp @($sshArgs + @($tarLocal, "${remote}:${tarRemote}"))
if ($LASTEXITCODE -ne 0) { throw "scp failed" }

$remoteShLocal = Join-Path $WorkspaceRoot "scripts\deploy-no1kmedi-remote-build_v1.sh"
if (-not (Test-Path $remoteShLocal)) { throw "missing remote build script: $remoteShLocal" }
$remoteShRemote = "/tmp/deploy-no1kmedi-remote-build_v1.sh"

Write-Host "[no1kmedi-tarball] remote build + pm2" -ForegroundColor Cyan
& scp @($sshArgs + @($remoteShLocal, "${remote}:${remoteShRemote}"))
if ($LASTEXITCODE -ne 0) { throw "scp remote build script failed" }
& ssh @($sshArgs + @($remote, "sed -i 's/\r$//' $remoteShRemote && bash $remoteShRemote $vpsParent $vpsDest $vpsDestinyRepo $tarRemote $stamp"))
if ($LASTEXITCODE -ne 0) { throw "remote deploy failed" }

Start-Sleep -Seconds 6
$smokeUrls = @(
    "https://app.jema-ai.com/safety",
    "https://app.jema-ai.com/validation",
    "https://app.jema-ai.com/enterprise",
    "https://app.jema-ai.com/clinician"
)
foreach ($entUrl in $smokeUrls) {
    Write-Host "[no1kmedi-tarball] smoke GET $entUrl" -ForegroundColor Cyan
    $httpCode = (& curl.exe -s -o NUL -w "%{http_code}" -L --max-time 30 $entUrl)
    if (@("200", "301", "302") -notcontains "$httpCode") {
        throw "[no1kmedi-tarball] smoke failed: $entUrl (http $httpCode)"
    }
}

if ($RunApiSmoke) {
    Write-Host "[no1kmedi-tarball] smoke POST advanced-consult (validate envelope)" -ForegroundColor Cyan
    $consultJson = @'
{"schema":"patient_consult_input_v1","request_id":"deploy_smoke","actor_id":"deploy","lane_a_profile":{"birth_instant_utc":"1987-12-31T15:00:00Z","iana_tz":"Asia/Seoul","constitution_survey":{"digestion_pattern":"post-meal bloating"}},"lane_b_clinical":{"chief_complaint":"chronic fatigue","onset":"6mo","severity":"moderate","medication":"none","health_survey":{"sleep_quality":"delayed sleep onset"}}}
'@
    $consultBody = Join-Path $env:TEMP "no1kmedi-deploy-consult-body-$stamp.json"
    [System.IO.File]::WriteAllText($consultBody, $consultJson.Trim(), [System.Text.UTF8Encoding]::new($false))
    $consultOut = Join-Path $env:TEMP "no1kmedi-deploy-consult-$stamp.json"
    $consultCode = (& curl.exe -s -o $consultOut -w "%{http_code}" --max-time 60 -X POST "https://app.jema-ai.com/api/cdss/advanced-consult?validate_km_cds_envelope=1" -H "Content-Type: application/json; charset=utf-8" -H "Origin: https://app.jema-ai.com" --data-binary "@$consultBody")
    if ($consultCode -ne "200") { throw "advanced-consult smoke failed http $consultCode" }
    $consult = Get-Content $consultOut -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $consult.km_cds.validation.ok) {
        throw "km_cds.validation not ok: $($consult.km_cds.validation.error)"
    }
    Write-Host "[no1kmedi-tarball] smoke POST patient-care-bundle-from-cds" -ForegroundColor Cyan
    $bundleReq = @{
        schema = "patient_care_bundle_from_cds_request_v1"
        request_id = "deploy_smoke"
        birth_instant_utc = "1987-12-31T15:00:00Z"
        iana_tz = "Asia/Seoul"
        cds_envelope = $consult.km_cds.envelope
        soap = @{
            subjective = @{ text = "chronic fatigue (deploy smoke)" }
            objective = @{ text = "not recorded" }
            assessment = @{ text = "preliminary hypothesis" }
            plan = @{ text = "physician confirmation" }
        }
        options = @{
            apply_slot_templates = $true
            validate_policy = $true
            validate_bundle = $true
            render_patient_md = $true
        }
    } | ConvertTo-Json -Depth 25 -Compress
    $bundleFile = Join-Path $env:TEMP "no1kmedi-deploy-bundle-$stamp.json"
    [System.IO.File]::WriteAllText($bundleFile, $bundleReq, [System.Text.UTF8Encoding]::new($false))
    $bundleOut = Join-Path $env:TEMP "no1kmedi-deploy-bundle-resp-$stamp.json"
    $bundleCode = (& curl.exe -s -o $bundleOut -w "%{http_code}" --max-time 90 -X POST "https://app.jema-ai.com/api/cdss/patient-care-bundle-from-cds" -H "Content-Type: application/json; charset=utf-8" -H "Origin: https://app.jema-ai.com" -H "Referer: https://app.jema-ai.com/clinician" --data-binary "@$bundleFile")
    if ($bundleCode -ne "200") { throw "patient-care-bundle smoke failed http $bundleCode" }
    $bundle = Get-Content $bundleOut -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $bundle.success) { throw "patient-care-bundle success=false" }
$mdLen = ($bundle.patient_facing_markdown | Out-String).Trim().Length
if ($mdLen -lt 20) { throw "patient_facing_markdown too short ($mdLen)" }

Write-Host "[no1kmedi-tarball] smoke POST clinician/graph/build-from-cds" -ForegroundColor Cyan
$graphBuildReq = @{
    schema = "clinician_graph_build_from_cds_request_v1"
    request_id = "deploy_smoke_graph_$stamp"
    cds_envelope = $consult.km_cds.envelope
    reasoning = @{
        syndrome_hypothesis = ($consult.draft.reasoning.syndrome_hypothesis | Out-String).Trim()
        care_direction = ($consult.draft.reasoning.care_direction | Out-String).Trim()
        caution = ($consult.draft.reasoning.caution | Out-String).Trim()
    }
    patient_care_bundle = $bundle.patient_care_bundle
    options = @{
        include_sasang_hint = $true
        include_conflict_paths = $true
        include_bundle_slots = $true
    }
} | ConvertTo-Json -Depth 30 -Compress
$graphBuildFile = Join-Path $env:TEMP "no1kmedi-deploy-graph-build-$stamp.json"
[System.IO.File]::WriteAllText($graphBuildFile, $graphBuildReq, [System.Text.UTF8Encoding]::new($false))
$graphBuildOut = Join-Path $env:TEMP "no1kmedi-deploy-graph-build-out-$stamp.json"
$graphBuildCode = (& curl.exe -s -o $graphBuildOut -w "%{http_code}" --max-time 60 -X POST "https://app.jema-ai.com/api/clinician/graph/build-from-cds" -H "Content-Type: application/json; charset=utf-8" -H "Origin: https://app.jema-ai.com" --data-binary "@$graphBuildFile")
if ($graphBuildCode -ne "200") { throw "graph build-from-cds smoke failed http $graphBuildCode" }
$graphBuild = Get-Content $graphBuildOut -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $graphBuild.success) { throw "graph build-from-cds success=false" }
Write-Host "[no1kmedi-tarball] smoke POST clinician/paste-extract-v1 (LLM chip)" -ForegroundColor Cyan
$pasteExtractBody = Join-Path $env:TEMP "no1kmedi-deploy-paste-extract-$stamp.json"
$pasteExtractJson = '{"chart_text":"Kim Minsu / 1988-03-12 / male / age 36 / back pain 3 weeks"}'
[System.IO.File]::WriteAllText($pasteExtractBody, $pasteExtractJson, [System.Text.UTF8Encoding]::new($false))
$pasteExtractOut = Join-Path $env:TEMP "no1kmedi-deploy-paste-extract-out-$stamp.json"
$pasteExtractCode = (& curl.exe -s -o $pasteExtractOut -w "%{http_code}" --max-time 90 -X POST "https://app.jema-ai.com/api/clinician/paste-extract-v1" -H "Content-Type: application/json; charset=utf-8" -H "Origin: https://app.jema-ai.com" -H "Referer: https://app.jema-ai.com/clinician?panel=gold" -H "x-clinician-email: smoke-paste-chart@local.test" --data-binary "@$pasteExtractBody")
if ($pasteExtractCode -eq "503") {
    Write-Host "[no1kmedi-tarball] paste-extract LLM disabled (503) — run Sync-No1kmediClinicianOpsEnvToVps_v1.ps1" -ForegroundColor Yellow
} elseif ($pasteExtractCode -ne "200") {
    throw "paste-extract smoke failed http $pasteExtractCode"
} else {
    $pasteExtract = Get-Content $pasteExtractOut -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $pasteExtract.success) { throw "paste-extract success=false" }
    Write-Host "[no1kmedi-tarball] paste-extract OK (provider=$($pasteExtract.provider))" -ForegroundColor Green
}

Write-Host "[no1kmedi-tarball] API smoke OK (md_len=$mdLen graph_nodes=$($graphBuild.graph_bundle_v1.nodes.Count))" -ForegroundColor Green
}

Remove-Item $tarLocal -Force -ErrorAction SilentlyContinue

Write-Host "[no1kmedi-tarball] logos ask quality bundle (shipped + VPS live)" -ForegroundColor Cyan
$bundlePy = Join-Path $WorkspaceRoot "scripts\run_logos_ask_quality_bundle_v1.py"
& py $bundlePy --live-vps
if ($LASTEXITCODE -ne 0) { throw "logos ask quality bundle failed (see reports/logos_ask_quality_bundle_v1_latest.json)" }

Write-Host "[no1kmedi-tarball] OK" -ForegroundColor Green
