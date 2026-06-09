<#
.SYNOPSIS
  NotebookLM 미니멀 포트폴리오 — 팩 빌드 · 상태 보드 · notebook_ids 맵 · (선택) Vault 미러.

.DESCRIPTION
  SSOT: docs/final/NOTEBOOKLM_MINIMAL_PORTFOLIO_V1.json
  산출: reports/notebooklm_portfolio_status_latest.md (운영 한 페이지)
        reports/notebooklm_lens_packs_v1/notebook_ids.json (nlm push용)

  Google NL 제목 정리·소스 prune는 UI 수동 — 본 스크립트는 레포 측만 동기화.

.PARAMETER SkipVaultMirror
  sync_notebooklm_sources_to_mkm_data_vault.ps1 생략

.PARAMETER PushToNotebookLm
  lens 팩 nlm push (DryRun 아님 — nlm 필요)

.PARAMETER DryRunPush
  Push-NotebooklmLensPacks_v1.ps1 -DryRun 만
#>
param(
  [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
  [switch]$SkipVaultMirror,
  [switch]$PushToNotebookLm,
  [switch]$DryRunPush
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

Write-Host "== NotebookLM Minimal Portfolio Routine ==" -ForegroundColor Cyan

Write-Host "[1/4] build lens packs" -ForegroundColor Cyan
& py scripts/build_notebooklm_lens_source_packs_v1.py
if ($LASTEXITCODE -ne 0) { throw "build_notebooklm_lens_source_packs_v1.py exit $LASTEXITCODE" }

Write-Host "[2/4] portfolio status + notebook_ids.json" -ForegroundColor Cyan
& py scripts/build_notebooklm_minimal_portfolio_status_v1.py --write-notebook-map
if ($LASTEXITCODE -ne 0) {
  Write-Host "WARN: portfolio status exit $LASTEXITCODE (check blockers in status JSON)" -ForegroundColor Yellow
}

if (-not $SkipVaultMirror) {
  Write-Host "[3/4] Vault mirror (optional)" -ForegroundColor Cyan
  $vaultScript = Join-Path $PSScriptRoot "sync_notebooklm_sources_to_mkm_data_vault.ps1"
  if (Test-Path -LiteralPath $vaultScript) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $vaultScript
    if ($LASTEXITCODE -ne 0) {
      Write-Host "WARN: Vault mirror exit $LASTEXITCODE" -ForegroundColor Yellow
    }
  } else {
    Write-Host "SKIP: $vaultScript not found" -ForegroundColor DarkYellow
  }
} else {
  Write-Host "[3/4] Vault mirror skipped" -ForegroundColor DarkGray
}

$pushScript = Join-Path $PSScriptRoot "Push-NotebooklmLensPacks_v1.ps1"
if ($PushToNotebookLm -or $DryRunPush) {
  Write-Host "[4/4] nlm lens push" -ForegroundColor Cyan
  $pushArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $pushScript)
  if ($DryRunPush) { $pushArgs += "-DryRun" }
  & powershell.exe @pushArgs
  if ($LASTEXITCODE -ne 0) { throw "Push-NotebooklmLensPacks_v1.ps1 exit $LASTEXITCODE" }
} else {
  Write-Host "[4/4] nlm push skipped ( -PushToNotebookLm or -DryRunPush )" -ForegroundColor DarkGray
}

$md = Join-Path $WorkspaceRoot "reports\notebooklm_portfolio_status_latest.md"
Write-Host ""
Write-Host "DONE. Open: $md" -ForegroundColor Green
Write-Host 'Google NL: rename notebooks to canonical_name; skip 99_ARCHIVE and deprecated UUIDs.' -ForegroundColor Cyan
