#Requires -Version 5.1
<#
.SYNOPSIS
  Track C Logos Observatory final commercialization bundle (not MS demo paste).
#>
$ErrorActionPreference = "Stop"
$root = "c:\workspace"
Set-Location $root

Write-Host "== [1/10] dynamic map -> showroom static ==" -ForegroundColor Cyan
py scripts/publish_logos_chronology_dynamic_map_showroom_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== [2/10] graph slice (commercial density) ==" -ForegroundColor Cyan
py scripts/build_showroom_meaning_topology_graph_slice_v1.py --seed-count 14 --max-nodes 72 --max-edges 140
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== [3/10] Q&A presets + era + reasoning paths ==" -ForegroundColor Cyan
py scripts/build_showroom_meaning_topology_qa_presets_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== [3b/10] graph-wire PoC (honest metrics) ==" -ForegroundColor Cyan
py scripts/build_mkm_graph_wire_rag_poc_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py -m pytest tests/test_build_mkm_graph_wire_rag_poc_v1.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== [4/10] B2B sales collateral (Track C) ==" -ForegroundColor Cyan
py scripts/build_track_c_logos_b2b_sales_collateral_v1.py
$collateralExit = $LASTEXITCODE

Write-Host "== [5/10] B2B meeting pack + readiness ==" -ForegroundColor Cyan
py scripts/build_track_c_b2b_meeting_pack_v1.py --skip-commander
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/check_track_c_b2b_meeting_pack_readiness_v1.py
$b2bExit = $LASTEXITCODE

Write-Host "== [6/10] deploy staging + VPS sync ==" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/deploy_showroom_static.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_showroom_to_vps.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== [7/10] public showroom smoke ==" -ForegroundColor Cyan
py scripts/check_showroom_trust_viz_public_chain_v1.py
$smokeExit = $LASTEXITCODE

Write-Host "== [8/10] trace API contract pytest ==" -ForegroundColor Cyan
py -m pytest tests/test_logos_trace_api_stub_v1.py -q
$traceExit = $LASTEXITCODE

Write-Host "== [9/10] commercial readiness gate ==" -ForegroundColor Cyan
py scripts/build_logos_observatory_commercial_readiness_v1.py
$readyExit = $LASTEXITCODE

Write-Host "== [10/10] product GIF (optional) ==" -ForegroundColor Cyan
py scripts/capture_oracle_v6_gif_v1.py
$gifExit = $LASTEXITCODE

Write-Host "Done collateral=$collateralExit b2b=$b2bExit smoke=$smokeExit trace=$traceExit ready=$readyExit gif=$gifExit" -ForegroundColor $(if ($readyExit -eq 0 -and $smokeExit -eq 0) { "Green" } else { "Yellow" })
exit $(if ($readyExit -eq 0) { 0 } else { $readyExit })
