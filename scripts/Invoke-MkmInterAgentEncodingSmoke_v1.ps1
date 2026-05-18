#Requires -Version 5.1
<#
.SYNOPSIS
  One-click MKM Inter-Agent Encoding smoke (RQ-019): pytest + status JSON + worked example emit.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmInterAgentEncodingSmoke_v1.ps1
#>
param(
    [switch]$SkipStatusBuild,
    [switch]$SkipWorkedExampleEmit,
    [switch]$SkipDialogueMock,
    [switch]$SkipL1ExperimentalPytest,
    [switch]$IncludeParallelLanes
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$tests = @(
    "tests/test_compression_token_api_v2_stub.py",
    "tests/test_build_mkm_inter_agent_encoding_status_v1.py",
    "tests/test_emit_mkm_inter_agent_first_message_worked_example_v1.py",
    "tests/test_run_mkm_inter_agent_dialogue_mock_v1.py"
)
Write-Host "== Inter-agent encoding pytest (3 files) ==" -ForegroundColor Cyan
py -m pytest @tests -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipStatusBuild) {
    Write-Host "== build_mkm_inter_agent_encoding_status_v1.py ==" -ForegroundColor Cyan
    py scripts/build_mkm_inter_agent_encoding_status_v1.py --strict-exit
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipWorkedExampleEmit) {
    Write-Host "== emit_mkm_inter_agent_first_message_worked_example_v1.py ==" -ForegroundColor Cyan
    py scripts/emit_mkm_inter_agent_first_message_worked_example_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipDialogueMock) {
    Write-Host "== run_mkm_inter_agent_dialogue_mock_v1.py ==" -ForegroundColor Cyan
    py scripts/run_mkm_inter_agent_dialogue_mock_v1.py --turns 4
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipL1ExperimentalPytest) {
    Write-Host "== L1 experimental expand (slow) ==" -ForegroundColor Cyan
    py -m pytest tests/test_compression_token_api_v2_stub.py::test_v2_expand_l1_experimental_mode_research_only -q --tb=short
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[DONE] Inter-agent encoding smoke OK" -ForegroundColor Green
