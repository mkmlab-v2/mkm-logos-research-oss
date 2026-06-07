#Requires -Version 5.1
<#
.SYNOPSIS
  B-track prophecy ops light refresh: ingest + shadow gates + pre-news + mkmlife envelope (no full daily chain).

.DESCRIPTION
  research_only · no live trading · no Track A promotion.
  Persona: Invoke-MkmPersonaHealth_v1.ps1 -Persona BtrackProphecyLightRefresh

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-BtrackProphecyOpsLightRefresh_v1.ps1
#>
param(
  [string]$WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
  [switch]$SkipNetworkIngest,
  [switch]$SkipDualLegBrief,
  [switch]$SkipMkmlifeEnvelope
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $WorkspaceRoot

$dotenv = Join-Path $WorkspaceRoot 'scripts\Import-WorkspaceDotEnv_v1.ps1'
if (Test-Path -LiteralPath $dotenv) { . $dotenv -WorkspaceRoot $WorkspaceRoot }

function Invoke-Step {
  param([string]$Desc, [scriptblock]$Block, [switch]$AllowFail)
  Write-Host "==> $Desc" -ForegroundColor Cyan
  & $Block
  if ($LASTEXITCODE -ne 0) {
    if ($AllowFail) {
      Write-Host "WARN: $Desc exit $LASTEXITCODE (continuing)." -ForegroundColor Yellow
    } else {
      throw "$Desc exit $LASTEXITCODE"
    }
  }
}

if (-not $SkipNetworkIngest) {
  $exaChain = Join-Path $WorkspaceRoot 'scripts\Run-BtrackExaMacroNewsChain_v1.ps1'
  if (Test-Path -LiteralPath $exaChain) {
    Invoke-Step 'Exa macro news chain' { & $exaChain -AppendStaging } -AllowFail:(-not $env:EXA_API_KEY)
  }
  Invoke-Step 'Naver OpenAPI signals' {
    py (Join-Path $WorkspaceRoot 'scripts\fetch_naver_openapi_signals_v1.py') --allow-cache-fallback
  } -AllowFail
} else {
  Invoke-Step 'news/macro lens adapters' {
    py (Join-Path $WorkspaceRoot 'scripts\build_btrack_news_macro_lens_adapters_v1.py')
  }
}

Invoke-Step 'hybrid research parallel R1-R5' {
  py (Join-Path $WorkspaceRoot 'scripts\run_btrack_hybrid_research_parallel_v1.py')
}
Invoke-Step 'hybrid today shadow digest' {
  py (Join-Path $WorkspaceRoot 'scripts\build_bbs_ms_hybrid_today_shadow_digest_v1.py')
}
Invoke-Step 'holdout gate candidate manifest' {
  py (Join-Path $WorkspaceRoot 'scripts\build_btrack_holdout_gate_candidate_manifest_v1.py')
}

$preNewsChain = Join-Path $WorkspaceRoot 'scripts\run_global_atom_pre_news_shadow_chain_v1.ps1'
if (Test-Path -LiteralPath $preNewsChain) {
  Invoke-Step 'pre-news shadow projection' { & $preNewsChain } -AllowFail
}
Invoke-Step 'pre-news ops status dashboard' {
  py (Join-Path $WorkspaceRoot 'scripts\build_pre_news_shadow_ops_status_dashboard_v1.py')
} -AllowFail

if (-not $SkipMkmlifeEnvelope) {
  Invoke-Step 'three_lens_sphere_envelope (+ mkmlife public copy)' {
    py (Join-Path $WorkspaceRoot 'scripts\assemble_three_lens_sphere_envelope_v1.py') --copy-mkmlife-public --validate-schema
  } -AllowFail
}

if (-not $SkipDualLegBrief) {
  $scoreJson = Join-Path $WorkspaceRoot 'docs\final\artifacts\btrack_prophecy_score_latest.json'
  if (Test-Path -LiteralPath $scoreJson) {
    $dualLeg = Join-Path $WorkspaceRoot 'scripts\Invoke-ProphecyDualLegAndKospiBrief_v1.ps1'
    Invoke-Step 'dual-leg prophecy brief + KOSPI morning onepager' { & $dualLeg -WorkspaceRoot $WorkspaceRoot }
  } else {
    Write-Host 'Skip dual-leg brief (missing btrack_prophecy_score_latest.json; run daily chain with hit-rate for full brief).' -ForegroundColor DarkYellow
    Invoke-Step 'internal KOSPI morning onepager (partial inputs OK)' {
      py (Join-Path $WorkspaceRoot 'scripts\build_internal_kospi_morning_brief_onepager_v1.py')
    } -AllowFail
  }
}

Write-Host 'OK: B-track prophecy ops light refresh complete.' -ForegroundColor Green
