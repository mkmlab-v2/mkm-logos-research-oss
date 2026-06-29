# Hot-reload Logos Studio UI to VPS (scss/tsx only, fast path).



param(

    [string]$Remote = "vps-mkmlife",

    [string]$AppRoot = "/opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi"

)



$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

$app = $AppRoot

$repo = Split-Path -Parent (Split-Path -Parent $app)



$files = @(

    @{ local = "projects\no1kmedi\src\app\globals.css"; remote = "$app/src/app/globals.css" },

    @{ local = "projects\no1kmedi\src\app\logos-research\page.tsx"; remote = "$app/src/app/logos-research/page.tsx" },

    @{ local = "projects\no1kmedi\src\app\logos-research\studio\page.tsx"; remote = "$app/src/app/logos-research/studio/page.tsx" },

    @{ local = "projects\no1kmedi\src\app\api\logos-research\query\route.ts"; remote = "$app/src/app/api/logos-research/query/route.ts" },

    @{ local = "projects\no1kmedi\src\app\api\logos-research\presets\route.ts"; remote = "$app/src/app/api/logos-research/presets/route.ts" },

    @{ local = "projects\no1kmedi\src\app\api\logos-research\evidence-feedback\route.ts"; remote = "$app/src/app/api/logos-research/evidence-feedback/route.ts" },

    @{ local = "projects\no1kmedi\src\app\api\telemetry\event\route.ts"; remote = "$app/src/app/api/telemetry/event/route.ts" },

    @{ local = "projects\no1kmedi\src\app\api\telemetry\summary\route.ts"; remote = "$app/src/app/api/telemetry/summary/route.ts" },

    @{ local = "projects\no1kmedi\marketing-site\logos-research-copy.json"; remote = "$app/marketing-site/logos-research-copy.json" },

    @{ local = "projects\no1kmedi\src\components\logos-research\LogosResearchStudioPageBody.tsx"; remote = "$app/src/components/logos-research/LogosResearchStudioPageBody.tsx" },

    @{ local = "projects\no1kmedi\src\components\logos-research\LogosResearchStudioClient.tsx"; remote = "$app/src/components/logos-research/LogosResearchStudioClient.tsx" },

    @{ local = "projects\no1kmedi\src\components\logos-research\LogosResearchSubgraphPanel.tsx"; remote = "$app/src/components/logos-research/LogosResearchSubgraphPanel.tsx" },

    @{ local = "projects\no1kmedi\src\components\logos-research\LogosResearchSubgraphPanel.tsx"; remote = "$app/src/components/logos-research/LogosResearchSubgraphPanel.tsx" },

    @{ local = "projects\no1kmedi\src\components\logos\LogosGraphStudioHeroInlineDemo.tsx"; remote = "$app/src/components/logos/LogosGraphStudioHeroInlineDemo.tsx" },
    @{ local = "projects\no1kmedi\src\components\logos-research\LogosResearchExploreMeshPanel.tsx"; remote = "$app/src/components/logos-research/LogosResearchExploreMeshPanel.tsx" },
    @{ local = "projects\no1kmedi\src\lib\useLogosStudioGraphSliceV1.ts"; remote = "$app/src/lib/useLogosStudioGraphSliceV1.ts" },
    @{ local = "projects\no1kmedi\src\lib\logosResearchExploreMeshV1.ts"; remote = "$app/src/lib/logosResearchExploreMeshV1.ts" },
    @{ local = "projects\no1kmedi\src\lib\logosResearchCitationDetailV1.ts"; remote = "$app/src/lib/logosResearchCitationDetailV1.ts" },
    @{ local = "projects\no1kmedi\src\lib\logosResearchVerseCitationShardV1.ts"; remote = "$app/src/lib/logosResearchVerseCitationShardV1.ts" },
    @{ local = "projects\no1kmedi\scripts\sync-logos-studio-data.mjs"; remote = "$app/scripts/sync-logos-studio-data.mjs" },
    @{ local = "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"; remote = "$repo/docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json" },
    @{ local = "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"; remote = "$repo/docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json" },
    @{ local = "docs/final/artifacts/showroom_meaning_topology_qa_router_sidecar_v1_latest.json"; remote = "$repo/docs/final/artifacts/showroom_meaning_topology_qa_router_sidecar_v1_latest.json" },
    @{ local = "docs/final/artifacts/lens_context_mesh_hop_index_logos_v1_latest.json"; remote = "$repo/docs/final/artifacts/lens_context_mesh_hop_index_logos_v1_latest.json" },
    @{ local = "docs/final/artifacts/logos_studio_semantic_router_lexical_index_v1_latest.json"; remote = "$repo/docs/final/artifacts/logos_studio_semantic_router_lexical_index_v1_latest.json" },
    @{ local = "docs/final/artifacts/logos_studio_semantic_router_embedding_index_v1_latest.json"; remote = "$repo/docs/final/artifacts/logos_studio_semantic_router_embedding_index_v1_latest.json" },
    @{ local = "docs/final/artifacts/logos_studio_verse_citation_shard_v1_latest.json"; remote = "$repo/docs/final/artifacts/logos_studio_verse_citation_shard_v1_latest.json" },
    @{ local = "projects\no1kmedi\public\data\logos_studio\graph_slice_v1.json"; remote = "$app/public/data/logos_studio/graph_slice_v1.json" },
    @{ local = "projects\no1kmedi\public\data\logos_studio\qa_presets_v1.json"; remote = "$app/public/data/logos_studio/qa_presets_v1.json" },
    @{ local = "projects\no1kmedi\public\data\logos_studio\qa_router_sidecar_v1.json"; remote = "$app/public/data/logos_studio/qa_router_sidecar_v1.json" },
    @{ local = "projects\no1kmedi\public\data\logos_studio\semantic_router_lexical_index_v1.json"; remote = "$app/public/data/logos_studio/semantic_router_lexical_index_v1.json" },
    @{ local = "projects\no1kmedi\public\data\logos_studio\semantic_router_embedding_index_v1.json"; remote = "$app/public/data/logos_studio/semantic_router_embedding_index_v1.json" },
    @{ local = "projects\no1kmedi\public\data\logos_studio\context_mesh_hop_index_v1.json"; remote = "$app/public/data/logos_studio/context_mesh_hop_index_v1.json" },
    @{ local = "projects\no1kmedi\public\data\logos_studio\verse_citation_shard_v1.json"; remote = "$app/public/data/logos_studio/verse_citation_shard_v1.json" },
    @{ local = "projects\no1kmedi\src\components\logos-research\LogosResearchCitationSidecarPanel.tsx"; remote = "$app/src/components/logos-research/LogosResearchCitationSidecarPanel.tsx" },
    @{ local = "projects\no1kmedi\package.json"; remote = "$app/package.json" },
    @{ local = "projects\no1kmedi\package-lock.json"; remote = "$app/package-lock.json" },

    @{ local = "projects\no1kmedi\src\components\logos-research\LogosResearchStoryboardPanel.tsx"; remote = "$app/src/components/logos-research/LogosResearchStoryboardPanel.tsx" },

    @{ local = "projects\no1kmedi\src\components\logos-research\LogosResearchConflictSidecarPanel.tsx"; remote = "$app/src/components/logos-research/LogosResearchConflictSidecarPanel.tsx" },

    @{ local = "projects\no1kmedi\src\lib\logosGraphStudioEmbed.ts"; remote = "$app/src/lib/logosGraphStudioEmbed.ts" },
    @{ local = "projects\no1kmedi\src\lib\logosStudioHeroDemoBeatsV1.ts"; remote = "$app/src/lib/logosStudioHeroDemoBeatsV1.ts" },
    @{ local = "projects\no1kmedi\src\lib\logosStudioEcsLowRequeryPocV1.ts"; remote = "$app/src/lib/logosStudioEcsLowRequeryPocV1.ts" },
    @{ local = "projects\no1kmedi\src\lib\logosResearchPathMindmapV1.ts"; remote = "$app/src/lib/logosResearchPathMindmapV1.ts" },
    @{ local = "projects\no1kmedi\src\lib\pathMindmapCoreV1.ts"; remote = "$app/src/lib/pathMindmapCoreV1.ts" },
    @{ local = "projects\no1kmedi\src\lib\logosResearchPathMindmapMeshV1.ts"; remote = "$app/src/lib/logosResearchPathMindmapMeshV1.ts" },
    @{ local = "projects\no1kmedi\src\lib\useLogosStudioGraphSliceV1.ts"; remote = "$app/src/lib/useLogosStudioGraphSliceV1.ts" },
    @{ local = "projects\no1kmedi\src\components\path-mindmap\PathMindmapSvgPanel.tsx"; remote = "$app/src/components/path-mindmap/PathMindmapSvgPanel.tsx" },
    @{ local = "projects\no1kmedi\src\components\logos-research\LogosResearchPathMindmapPanel.tsx"; remote = "$app/src/components/logos-research/LogosResearchPathMindmapPanel.tsx" },
    @{ local = "projects\no1kmedi\src\lib\logosResearchQuotaV1.ts"; remote = "$app/src/lib/logosResearchQuotaV1.ts" },

    @{ local = "projects\no1kmedi\src\lib\logosStudioGraphCoverageV1.ts"; remote = "$app/src/lib/logosStudioGraphCoverageV1.ts" },

    @{ local = "projects\no1kmedi\src\lib\logosStudioConflictBridgeV1.ts"; remote = "$app/src/lib/logosStudioConflictBridgeV1.ts" },

    @{ local = "projects\no1kmedi\src\lib\logosResearchStudioDisplayV1.ts"; remote = "$app/src/lib/logosResearchStudioDisplayV1.ts" },

    @{ local = "projects\no1kmedi\src\lib\logosResearchStudioV1.ts"; remote = "$app/src/lib/logosResearchStudioV1.ts" },

    @{ local = "projects\no1kmedi\src\lib\logosStudioSynthesisBridgeV1.ts"; remote = "$app/src/lib/logosStudioSynthesisBridgeV1.ts" },

    @{ local = "scripts\patch_logos_studio_graph_slice_router_verse_stubs_v1.py"; remote = "$repo/scripts/patch_logos_studio_graph_slice_router_verse_stubs_v1.py" },
    @{ local = "scripts\merge_logos_studio_embed_router_sidecar_v1.py"; remote = "$repo/scripts/merge_logos_studio_embed_router_sidecar_v1.py" },
    @{ local = "scripts\compute_logos_reasoning_path_v1.py"; remote = "$repo/scripts/compute_logos_reasoning_path_v1.py" },
    @{ local = "scripts\check_logos_studio_graph_slice_router_coverage_v1.py"; remote = "$repo/scripts/check_logos_studio_graph_slice_router_coverage_v1.py" },
    @{ local = "scripts\logos_studio_preset_graph_helpers_v1.py"; remote = "$repo/scripts/logos_studio_preset_graph_helpers_v1.py" },
    @{ local = "scripts\lens_context_mesh_v1.py"; remote = "$repo/scripts/lens_context_mesh_v1.py" },

    @{ local = "scripts\retrieve_logos_studio_conflict_context_v1.py"; remote = "$repo/scripts/retrieve_logos_studio_conflict_context_v1.py" },

    @{ local = "scripts\synthesize_logos_studio_dynamic_answer_v1.py"; remote = "$repo/scripts/synthesize_logos_studio_dynamic_answer_v1.py" },

    @{ local = "scripts\check_logos_studio_conflict_retrieval_gate_v1.py"; remote = "$repo/scripts/check_logos_studio_conflict_retrieval_gate_v1.py" }

)



$mkdirCmd = "mkdir -p $app/src/app/api/logos-research/evidence-feedback $app/src/components/logos-research $app/src/components/logos $app/src/components/path-mindmap $app/src/lib $app/public/data/logos_studio"

& ssh -o BatchMode=yes $Remote $mkdirCmd

if ($LASTEXITCODE -ne 0) { throw "remote mkdir failed exit $LASTEXITCODE" }



foreach ($f in $files) {

    $src = Join-Path $root $f.local

    if (-not (Test-Path $src)) { throw "missing: $src" }

    & scp -o BatchMode=yes $src "${Remote}:$($f.remote)"

    if ($LASTEXITCODE -ne 0) { throw "scp failed: $($f.local)" }

}



$remoteCmd = "rm -f $app/src/lib/LogosResearchStudioClient.tsx; rm -rf $app/.next; cd $app && npm install && npm run build && pm2 restart no1kmedi-com"



Write-Host "[logos-hotreload] build + pm2 on $Remote" -ForegroundColor Cyan

& ssh -o BatchMode=yes $Remote $remoteCmd

if ($LASTEXITCODE -ne 0) { throw "hot reload failed exit $LASTEXITCODE" }



$out = Join-Path $root "reports\logos_studio_hotreload_latest.json"

@{

    schema = "logos_studio_hotreload_v1"

    ok = $true

    remote = $Remote

    app_root = $AppRoot

    files = ($files | ForEach-Object { $_.local })

    reproduce = "powershell -File scripts/Invoke-LogosStudioHotReload_v1.ps1"

} | ConvertTo-Json | Set-Content -Path $out -Encoding UTF8

Write-Host "WROTE: $out"

