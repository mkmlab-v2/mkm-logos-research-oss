#Requires -Version 5.1
<#
.SYNOPSIS
  Philosophy / counsel lane RAG pilot (Track B, Fact-Lock).

.DESCRIPTION
  Thin wrapper over scripts/philosophy_lane_rag_pilot_v1.py.
  Does not call trading APIs. Writes docs/final/artifacts/philosophy_lane_rag_pilot_v1_latest.json by default.

.EXAMPLE
  pwsh -File scripts/run_philosophy_lane_rag_pilot_v1.ps1 -UserQuery "삶의 의미에 대해 조언해줘"
  pwsh -File scripts/run_philosophy_lane_rag_pilot_v1.ps1 -UserQuery "..." -InvokeCrossLensFusion
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$UserQuery,
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$MenuId = "mkm_philosophy_chat_v1",
    [int]$TopK = 3,
    [switch]$InvokeCrossLensFusion,
    [switch]$RedactQuery,
    [string]$ForbiddenConfig = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location -LiteralPath $WorkspaceRoot

$argsList = @(
    "scripts/philosophy_lane_rag_pilot_v1.py",
    "--user-query", $UserQuery,
    "--menu-id", $MenuId,
    "--top-k", "$TopK"
)
if ($InvokeCrossLensFusion) { $argsList += "--invoke-cross-lens-fusion" }
if ($RedactQuery) { $argsList += "--redact-query" }
if ($ForbiddenConfig -ne "") {
    $argsList += "--forbidden-config", $ForbiddenConfig
}

& py @argsList
if ($LASTEXITCODE -ne 0) { throw "philosophy_lane_rag_pilot_v1.py exit $LASTEXITCODE" }
