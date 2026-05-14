<#
.SYNOPSIS
  MKM 권장 하이브리드: 렌즈 팩(결정론) + Vault 미러 + 수동 NL/MCP 안내 + (선택) Track C 퓨전 스모크.

.DESCRIPTION
  Phase 1 — 로컬: `Run-NotebookLmLensPacksAndVaultMirror_v1.ps1` (팩 빌드 + `sync_notebooklm_sources_to_mkm_data_vault.ps1`, Vault 실패 시 자식 스크립트가 경고만).
  Phase 2 — (선택) 자동: PATH에 `nlm` 있고 `reports/notebooklm_lens_packs_v1/notebook_ids.json` 있으면 `Push-NotebooklmLensPacks_v1.ps1`로 **Google NL 소스 추가**(FusionHubBulk·Athena onefile과 동일 CLI). 최초: `Push-NotebooklmLensPacks_v1.ps1 -InitMap` 후 UUID 편집.
  Phase 2b — 수동: `nlm`/맵 미사용 시 웹에서 `source_add` (`docs/NotebookLM_sources_manifest.md` 표).
  Phase 3 — 수동: Cursor MCP `get_health` 후 **노트(렌즈)마다** `ask_question` + 고정 `notebook_id`. 성경(Logos)은 `[NON_GATING]`·브리핑만.
  Phase 4 — (선택) 레포 측 퓨전 증거: `run_workspace_automation_health.ps1 -TrackCMacroFusionSmokeOnly` (느림; Logos 번들 생략은 AGENTS.md·`.env` 참고).

  NotebookLM은 브리핑·RAG 층이며, 구현·게이트 SSOT는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·`.py`만.

.PARAMETER WorkspaceRoot
  모노레포 루트 (기본: 본 스크립트의 상위 디렉터리).

.PARAMETER SkipVaultMirror
  Phase 1에서 Vault 미러만 생략 (`Run-NotebookLmLensPacksAndVaultMirror_v1.ps1`에 전달).

.PARAMETER SkipLocalDeterministic
  Phase 1 전체 생략 (수동 점검 JSON만 갱신·선택 Phase 4만 실행 가능).

.PARAMETER IncludeTrackCMacroFusionSmoke
  Phase 1(및 선택적 Phase 4) 후 Track C 매크로 퓨전 스모크 실행 (로컬 체인·시간 소요).

.PARAMETER PushLensPacksToNotebookLm
  Phase 1 직후 `Push-NotebooklmLensPacks_v1.ps1` 실행(`reports/.../notebook_ids.json` 필요). 없으면 스킵 안내.

.PARAMETER NotebookLmLensPushDryRun
  `-PushLensPacksToNotebookLm`과 함께: `nlm` 호출 없이 푸시 계획만 로그.

.PARAMETER OutJson
  체크리스트 JSON 경로 (기본: reports/notebooklm_mkm_hybrid_routine_latest.json).

.NOTES
  프리미엄 멀티렌즈·큐 번들은 `Invoke-MkmPersonaHealth_v1.ps1 -Persona PremiumMultilensQueue` (AGENTS.md 표).
#>
param(
  [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
  [switch]$SkipVaultMirror,
  [switch]$SkipLocalDeterministic,
  [switch]$IncludeTrackCMacroFusionSmoke,
  [switch]$PushLensPacksToNotebookLm,
  [switch]$NotebookLmLensPushDryRun,
  [string]$OutJson = ""
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if (-not $OutJson) {
  $OutJson = Join-Path $WorkspaceRoot "reports\notebooklm_mkm_hybrid_routine_latest.json"
}

$stamp = [DateTime]::UtcNow.ToString("o")
$phases = New-Object System.Collections.ArrayList

function Add-Phase($id, [string]$status, [string]$note) {
  [void]$phases.Add([ordered]@{
      id     = $id
      status = $status
      note   = $note
    })
}

Write-Host "== MKM hybrid NotebookLM routine v1 ($stamp) ==" -ForegroundColor Cyan

if (-not $SkipLocalDeterministic) {
  $lensRunner = Join-Path $PSScriptRoot "Run-NotebookLmLensPacksAndVaultMirror_v1.ps1"
  Write-Host "Phase 1: lens packs + Vault mirror -> $lensRunner" -ForegroundColor Cyan
  $args = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $lensRunner,
    "-WorkspaceRoot", $WorkspaceRoot
  )
  if ($SkipVaultMirror) { $args += "-SkipVaultMirror" }
  & powershell.exe @args
  if ($LASTEXITCODE -ne 0) {
    Add-Phase "local_packs_vault" "failed" "exit_code=$LASTEXITCODE"
    throw "Run-NotebookLmLensPacksAndVaultMirror_v1.ps1 failed with exit $LASTEXITCODE"
  }
  Add-Phase "local_packs_vault" "ok" "build_notebooklm_lens_source_packs_v1 + sync_notebooklm_sources (Vault may warn)"
}
else {
  Add-Phase "local_packs_vault" "skipped" "-SkipLocalDeterministic"
}

$mapPath = Join-Path $WorkspaceRoot "reports\notebooklm_lens_packs_v1\notebook_ids.json"
if ($PushLensPacksToNotebookLm) {
  $pushScript = Join-Path $PSScriptRoot "Push-NotebooklmLensPacks_v1.ps1"
  if (-not (Test-Path -LiteralPath $mapPath)) {
    Write-Warning "PushLensPacksToNotebookLm: missing $mapPath — run: powershell -File scripts/Push-NotebooklmLensPacks_v1.ps1 -InitMap"
    Add-Phase "nl_nlm_push" "skipped" "missing notebook_ids.json (use -InitMap on Push-NotebooklmLensPacks_v1.ps1)"
  }
  else {
    Write-Host "Phase 2: nlm lens pack push -> $pushScript" -ForegroundColor Cyan
    $pargs = @(
      "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $pushScript,
      "-WorkspaceRoot", $WorkspaceRoot
    )
    if ($NotebookLmLensPushDryRun) { $pargs += "-DryRun" }
    & powershell.exe @pargs
    if ($LASTEXITCODE -ne 0) {
      Add-Phase "nl_nlm_push" "failed" "exit_code=$LASTEXITCODE see reports/notebooklm_lens_pack_push_latest.log"
      throw "Push-NotebooklmLensPacks_v1.ps1 failed with exit $LASTEXITCODE"
    }
    Add-Phase "nl_nlm_push" "ok" "Push-NotebooklmLensPacks_v1.ps1 (dry_run=$NotebookLmLensPushDryRun)"
  }
}
else {
  Add-Phase "nl_nlm_push" "skipped" "pass -PushLensPacksToNotebookLm to run nlm push when notebook_ids.json exists"
}

Add-Phase "manual_nl_upload" "human" "If nlm push not used: upload reports/notebooklm_lens_packs_v1/* per docs/NotebookLM_sources_manifest.md"
Add-Phase "manual_mcp_probe" "human" "MCP get_health; per-lens ask_question with notebook_id (new chat if tools missing)"

if ($IncludeTrackCMacroFusionSmoke) {
  $health = Join-Path $PSScriptRoot "run_workspace_automation_health.ps1"
  Write-Host "Phase 4: Track C macro fusion smoke -> $health" -ForegroundColor Cyan
  if (Get-Command pwsh -ErrorAction SilentlyContinue) {
    & pwsh -NoProfile -ExecutionPolicy Bypass -File $health -TrackCMacroFusionSmokeOnly
  }
  else {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $health -TrackCMacroFusionSmokeOnly
  }
  if ($LASTEXITCODE -ne 0) {
    Add-Phase "trackc_fusion_smoke" "failed" "exit_code=$LASTEXITCODE"
    throw "TrackCMacroFusionSmokeOnly failed with exit $LASTEXITCODE"
  }
  Add-Phase "trackc_fusion_smoke" "ok" "run_workspace_automation_health.ps1 -TrackCMacroFusionSmokeOnly"
}
else {
  Add-Phase "trackc_fusion_smoke" "skipped" "pass -IncludeTrackCMacroFusionSmoke to run; or PremiumMultilensQueue per AGENTS.md"
}

$dir = Split-Path -Parent $OutJson
if ($dir -and -not (Test-Path -LiteralPath $dir)) {
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$payload = [ordered]@{
  schema            = "notebooklm_mkm_hybrid_routine_v1"
  version           = "1.0.0"
  generated_at_utc  = $stamp
  workspace_root    = $WorkspaceRoot
  skip_vault_mirror = [bool]$SkipVaultMirror
  phases            = @($phases.ToArray())
  pointers          = [ordered]@{
    manifest = "docs/NotebookLM_sources_manifest.md"
    lens_packs = "reports/notebooklm_lens_packs_v1/"
    nlm_lens_push = "scripts/Push-NotebooklmLensPacks_v1.ps1"
    lens_notebook_map_template = "docs/final/notebooklm_lens_pack_push_map_v1.template.json"
    constitution = "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
    agents_personas = "AGENTS.md (Invoke-MkmPersonaHealth_v1.ps1)"
  }
}

$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutJson -Encoding utf8
Write-Host "Wrote $OutJson" -ForegroundColor Green
Write-Host "Done." -ForegroundColor Green
