#Requires -Version 5.1
<#
.SYNOPSIS
  Auto-progress offline_4d_knn candidate edges: review approve → signoff (saturation ack) → gate → pending JSONL.
  Canonical merge OFF by default (B-track staging). Use -IncludeCanonicalMerge to append canonical.
#>
param(
  [string]$Approver = "commander_auto_staging",
  [switch]$IncludeCanonicalMerge,
  [switch]$RefreshAgentSearch
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$argsList = @(
  "scripts/run_logos_candidate_edge_offline_4d_auto_promote_chain_v1.py",
  "--approver", $Approver
)
if ($IncludeCanonicalMerge) { $argsList += "--include-canonical-merge" }

py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($RefreshAgentSearch) {
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-AgentSearchCorpusUploadAndImport_v1.ps1 `
    -Profile logos-ops -SkipGemini `
    -Query "offline 4d knn pending promotion" `
    -Question "What is the offline_4d_knn auto promote chain status?"
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[OK] offline_4d_knn -> pending JSONL (canonical merge: $($IncludeCanonicalMerge.IsPresent))" -ForegroundColor Green
exit 0
