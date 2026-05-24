# LOGOS-100PCT Phase2: second concept_bridge + registry + subgraph GraphRAG router
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } else { 'python' }

& $py scripts/build_logos_concept_bridge_semiconductor_poc_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py scripts/build_logos_concept_bridge_covenant_crisis_poc_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py scripts/build_logos_concept_bridge_registry_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py scripts/build_logos_lemma_verse_edges_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py scripts/run_logos_subgraph_graphrag_router_v1.py --query-id q01
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py -m pytest tests/test_run_logos_subgraph_graphrag_router_v1.py tests/test_build_logos_concept_bridge_registry_v1.py -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py scripts/build_logos_100pct_closure_v1.py --run-pytest --strict
exit $LASTEXITCODE
