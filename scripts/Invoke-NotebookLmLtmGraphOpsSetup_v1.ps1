<#
.SYNOPSIS
  Build LTM Graph OS NotebookLM command pack (local) and optionally push via nlm CLI.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-NotebookLmLtmGraphOpsSetup_v1.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-NotebookLmLtmGraphOpsSetup_v1.ps1 -PushNlm
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-NotebookLmLtmGraphOpsSetup_v1.ps1 -PushNlm -DryRun
#>
param(
  [string]$WorkspaceRoot = "",
  [switch]$PushNlm,
  [switch]$DryRun,
  [switch]$RunVaultMirror
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
  $WorkspaceRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
}
Set-Location -LiteralPath $WorkspaceRoot

function Invoke-Step([string]$Name, [scriptblock]$Block) {
  Write-Host "== $Name" -ForegroundColor Cyan
  & $Block
  if ($LASTEXITCODE -ne 0) { throw "$Name failed exit=$LASTEXITCODE" }
}

Invoke-Step "bench refresh (token+route)" {
  py scripts/bench_mkm_ltm_resume_lane_token_v1.py
  py scripts/bench_mkm_ltm_route_accuracy_v1.py
}
Invoke-Step "ltm graph index md" { py scripts/build_notebooklm_ltm_graph_index_v1.py }
Invoke-Step "lens packs" { py scripts/build_notebooklm_lens_source_packs_v1.py }
Invoke-Step "materialize LTM_GRAPH_OPS" { py scripts/build_notebooklm_ltm_graph_ops_pack_v1.py }

$mapPath = Join-Path $WorkspaceRoot "reports\notebooklm_lens_packs_v1\notebook_ids.json"
if (-not (Test-Path -LiteralPath $mapPath)) {
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Push-NotebooklmLensPacks_v1.ps1") -InitMap
}

$packDir = Join-Path $WorkspaceRoot "reports\notebooklm_lens_packs_v1\LTM_GRAPH_OPS"
Write-Host "PACK: $packDir" -ForegroundColor Green
Get-ChildItem -LiteralPath $packDir -File | ForEach-Object { Write-Host "  - $($_.Name) ($($_.Length) bytes)" }

if ($RunVaultMirror) {
  Invoke-Step "vault mirror" {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1
  }
}

if ($PushNlm) {
  $pushArgs = @("scripts/push_notebooklm_ltm_graph_ops_nlm_v1.py")
  if ($DryRun) { $pushArgs += "--dry-run" }
  Invoke-Step "nlm push LTM_GRAPH_OPS" { py @pushArgs }
}
else {
  Write-Host "SKIP nlm push (use -PushNlm). Manual: upload files under reports/notebooklm_lens_packs_v1/LTM_GRAPH_OPS/" -ForegroundColor Yellow
  Write-Host "MCP: get_health -> setup_auth if needed -> add_source type=text per pack file" -ForegroundColor Yellow
}

Write-Host "DONE Invoke-NotebookLmLtmGraphOpsSetup_v1" -ForegroundColor Green
