#Requires -Version 5.1
<#
.SYNOPSIS
  Parallel bundle: denser graph slice, era presets, deploy VPS, v6 GIF, paste readiness.
#>
$ErrorActionPreference = "Stop"
$root = "c:\workspace"
Set-Location $root

Write-Host "== [1/5] graph slice (72 nodes cap) + verse snippets ==" -ForegroundColor Cyan
py scripts/build_showroom_meaning_topology_graph_slice_v1.py --seed-count 14 --max-nodes 72 --max-edges 140
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== [2/5] Q&A presets (+11 era) + reasoning paths ==" -ForegroundColor Cyan
py scripts/build_showroom_meaning_topology_qa_presets_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== [3/5] deploy + VPS sync ==" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/deploy_showroom_static.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
# RefreshStaging resets graph slice via track_c bundle — skip for dense commercial graph
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_showroom_to_vps.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== [4/5] v6 GIF capture (playwright) ==" -ForegroundColor Cyan
py scripts/capture_oracle_v6_gif_v1.py
$gifExit = $LASTEXITCODE

Write-Host "== [5/5] public smoke + paste readiness ==" -ForegroundColor Cyan
py scripts/check_showroom_trust_viz_public_chain_v1.py
$smokeExit = $LASTEXITCODE
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MsRq019PastePackReadiness_v1.ps1
$pasteExit = $LASTEXITCODE

Write-Host "Done. gif_exit=$gifExit smoke_exit=$smokeExit paste_exit=$pasteExit" -ForegroundColor $(if ($gifExit -eq 0 -and $smokeExit -eq 0 -and $pasteExit -eq 0) { "Green" } else { "Yellow" })
exit $(if ($smokeExit -eq 0) { 0 } else { $smokeExit })
