# List git paths for a focused Track C showroom commit (stdout only; no git add).
param([string]$WorkspaceRoot = "C:\workspace")
Set-Location $WorkspaceRoot
$patterns = @(
    "scripts/build_showroom_meaning_topology_graph_slice_v1.py",
    "scripts/build_showroom_track_c_bundle_chain_v1.ps1",
    "scripts/Invoke-ShowroomTrackC*.ps1",
    "scripts/Verify-ShowroomTrackC*.ps1",
    "scripts/Register-ShowroomTrackC*.ps1",
    "scripts/check_showroom_trust_viz_public_chain_v1.py",
    "scripts/build_showroom_track_c_ops_status_v1.py",
    "scripts/Show-ShowroomTrackCGitScope_v1.ps1",
    "docs/final/schemas/showroom_meaning_topology_graph_slice_v1.schema.json",
    "docs/final/artifacts/jemaai_showroom_public_urls_v1_latest.json",
    "docs/final/artifacts/track_c_showroom_topology_sales_demo_script_v1_latest.md",
    "tests/test_build_showroom_meaning_topology_graph_slice_v1.py",
    ".github/workflows/showroom-bundle-validate.yml",
    ".github/workflows/showroom-public-smoke.yml",
    "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_meaning_topology_graph_v1.html",
    "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/nginx_snippets/jemaai_showroom_ui.conf",
    "projects/bitcoin-trading/ops/windows-rehearsal/sync_showroom_to_vps.ps1",
    "projects/bitcoin-trading/ops/windows-rehearsal/deploy_showroom_static.ps1",
    "projects/bitcoin-trading/ops/windows-rehearsal/build_showroom_display_bundle.ps1",
    "projects/bitcoin-trading/ops/windows-rehearsal/verify_showroom_bundle_chain.ps1",
    "projects/bitcoin-trading/ops/windows-rehearsal/publish_showroom_public_event.ps1",
    "scripts/verify_p0_constitution_gate_paths.ps1",
    "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
    "AGENTS.md"
)
foreach ($p in $patterns) {
    git status --short -- $p 2>$null
}
