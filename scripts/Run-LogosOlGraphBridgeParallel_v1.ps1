# Parallel: concept bridge PoC + corpus bundle + graph wire profile + pytest
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$trackBridge = {
    Set-Location $using:root
    $py = $using:py
    $r = $using:root
    & $py "$r\scripts\build_logos_concept_bridge_semiconductor_poc_v1.py" --run-seed-chain
    if ($LASTEXITCODE -ne 0) { throw "concept bridge" }
}

$trackCorpus = {
    Set-Location $using:root
    $py = $using:py
    $r = $using:root
    if (Test-Path "$r\docs\final\artifacts\logos_corpus_manifest_v1_latest.json") {
        & $py "$r\scripts\build_logos_corpus_graph_bundle_v1.py"
        if ($LASTEXITCODE -ne 0) { throw "graph bundle" }
    }
}

$trackWire = {
    Set-Location $using:root
    $py = $using:py
    $r = $using:root
    & $py "$r\scripts\build_logos_graph_wire_profile_v1.py"
    if ($LASTEXITCODE -ne 0) { throw "wire profile" }
}

Write-Host "[ol-bridge] phase 1: concept bridge + corpus bundle + wire profile (parallel)"
$j1 = Start-Job -Name ConceptBridge -ScriptBlock $trackBridge
$j2 = Start-Job -Name CorpusBundle -ScriptBlock $trackCorpus
$j3 = Start-Job -Name WireProfile -ScriptBlock $trackWire
Wait-Job -Job $j1, $j2, $j3 | Out-Null
foreach ($j in @($j1, $j2, $j3)) {
    if ($j.State -eq "Failed") {
        Receive-Job -Job $j -ErrorAction SilentlyContinue | Write-Host
        throw "Job $($j.Name) failed"
    }
    Receive-Job -Job $j | Write-Host
    Remove-Job -Job $j
}

Write-Host "[ol-bridge] phase 2: original-language atoms summary (if inputs exist)"
$verse = "$root\data\logos\verse_decoded_v2.jsonl"
if (Test-Path -LiteralPath $verse) {
    & $py "$root\scripts\core\build_original_language_master_atoms.py"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "SKIP: $verse missing"
}

Write-Host "[ol-bridge] phase 3: pytest"
& $py -m pytest tests/test_logos_concept_bridge_v1.py tests/test_logos_corpus_graph_bundle_v1.py -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: Logos OL GraphRAG bridge parallel complete"
