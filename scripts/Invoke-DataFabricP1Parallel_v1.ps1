# DF-P1 parallel: seed chain + selective corpus load + wire profile + pytest
param(
    [switch]$SkipCorpusLoad,
    [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$steps = @(
    @{ Name = "DF-P1-01-seed-chain"; Cmd = @("py", "scripts/run_logos_graph_seed_chain_v1.py") },
    @{ Name = "DF-P1-03-wire-profile"; Cmd = @("py", "scripts/build_logos_graph_wire_profile_v1.py") }
)
if (-not $SkipCorpusLoad) {
    $steps = @(
        @{ Name = "DF-P1-01-seed-chain"; Cmd = @("py", "scripts/run_logos_graph_seed_chain_v1.py") },
        @{ Name = "DF-P1-02-corpus-load"; Cmd = @("py", "scripts/load_verse_corpus_by_ids_v1.py") },
        @{ Name = "DF-P1-03-wire-profile"; Cmd = @("py", "scripts/build_logos_graph_wire_profile_v1.py") }
    )
}

$failed = @()
foreach ($s in $steps) {
    Write-Host "== $($s.Name) ==" -ForegroundColor Cyan
    & $s.Cmd[0] $s.Cmd[1..($s.Cmd.Length - 1)]
    if ($LASTEXITCODE -ne 0) {
        $failed += $s.Name
    }
}

if (-not $SkipPytest) {
    Write-Host "== DF-P1-pytest ==" -ForegroundColor Cyan
    py -m pytest tests/test_run_logos_graph_seed_chain_v1.py tests/test_load_verse_corpus_by_ids_v1.py tests/test_build_mkm_graph_wire_rag_poc_v1.py -q
    if ($LASTEXITCODE -ne 0) {
        $failed += "DF-P1-pytest"
    }
}

if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "DF-P1 parallel OK" -ForegroundColor Green
exit 0
