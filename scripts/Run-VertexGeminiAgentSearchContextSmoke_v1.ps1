#Requires -Version 5.1
<#
.SYNOPSIS
  Smoke: Agent Search retrieval + context (optionally Vertex Gemini).

  Default uses MKM lab IDs; override with parameters.

.EXAMPLE
  pwsh -NoProfile -File scripts/Run-VertexGeminiAgentSearchContextSmoke_v1.ps1 -SkipGemini

.EXAMPLE
  pwsh -NoProfile -File scripts/Run-VertexGeminiAgentSearchContextSmoke_v1.ps1 -PullGcsPdfText -SkipGemini
#>
param(
  [string] $Project = "mkm-lab-agi-2025",
  [string] $EngineId = "b2g-search-mkm-lab-agi-2025",
  [string] $Query = "MKM",
  [string] $Question = "What is the indexed document title? One short phrase.",
  [switch] $SkipGemini,
  [switch] $PullGcsPdfText,
  [ValidateSet("documents", "chunks", "hybrid")]
  [string] $ContextMode = "hybrid"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$pyArgs = @(
  "scripts/run_vertex_gemini_agent_search_context_v1.py"
  "--project", $Project
  "--engine-id", $EngineId
  "--query", $Query
  "--question", $Question
  "--context-mode", $ContextMode
)
if ($SkipGemini) { $pyArgs += "--skip-gemini" }
if ($PullGcsPdfText) { $pyArgs += "--pull-gcs-pdf-text" }

py @pyArgs
exit $LASTEXITCODE
