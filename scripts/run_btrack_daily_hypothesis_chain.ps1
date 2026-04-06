# B-Track daily chain: independent lenses -> fusion stub -> LLM bundle (S1_SHADOW / observation only).
# Does not call LLM; prepare artifacts for manual or batch LLM step.
# Prerequisites: py on PATH, workspace = C:\workspace (or set $WorkspaceRoot).
#
# Task Scheduler (example, adjust time / user):
#   Program: pwsh.exe
#   Arguments: -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\run_btrack_daily_hypothesis_chain.ps1"
#   Working directory: C:\workspace
# Dawn scoring (separate task): build score JSON from OHLCV + yesterday hypothesis, then:
#   py scripts/eval_prophecy_hit_rate_v1.py --run-mode price --score-json path\to\score.json
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [switch]$SkipInsightAppend,
  [switch]$SkipHitRate
)
$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

Write-Host "==> run_lens_myeongni.py"
py scripts/run_lens_myeongni.py
if ($LASTEXITCODE -ne 0) { throw "run_lens_myeongni exit $LASTEXITCODE" }

Write-Host "==> run_lens_sasang.py"
py scripts/run_lens_sasang.py
if ($LASTEXITCODE -ne 0) { throw "run_lens_sasang exit $LASTEXITCODE" }

Write-Host "==> run_lens_logos.py"
py scripts/run_lens_logos.py
if ($LASTEXITCODE -ne 0) { throw "run_lens_logos exit $LASTEXITCODE" }

Write-Host "==> report_independent_lens_fusion_stub_v0.py"
py scripts/report_independent_lens_fusion_stub_v0.py
if ($LASTEXITCODE -ne 0) { throw "fusion stub exit $LASTEXITCODE" }

Write-Host "==> build_btrack_llm_input_bundle.py"
py scripts/build_btrack_llm_input_bundle.py
if ($LASTEXITCODE -ne 0) { throw "bundle exit $LASTEXITCODE" }

Write-Host "==> generate_btrack_hypothesis_prophecy_v1.py (stub; use --gemini for API)"
py scripts/generate_btrack_hypothesis_prophecy_v1.py
if ($LASTEXITCODE -ne 0) { throw "hypothesis gen exit $LASTEXITCODE" }

if (-not $SkipInsightAppend) {
  $summary = "daily_chain: myeongni+sasang+logos artifacts + fusion stub -> btrack_llm_input_bundle_latest.json"
  $liner = "[HYPO] Independent lens scores fused (observation_only); LLM may read bundle only — not live trading."
  $hook = "If fusion consensus disagrees with forward realized direction over N days, downgrade lens weight in review only."
  py scripts/append_btrack_insight_observation.py `
    --inputs-summary $summary `
    --insight-one-liner $liner `
    --falsification-hook $hook `
    --note "run_btrack_daily_hypothesis_chain.ps1"
  if ($LASTEXITCODE -ne 0) { throw "append insight exit $LASTEXITCODE" }
}

if (-not $SkipHitRate) {
  Write-Host "==> eval_prophecy_hit_rate_v1.py (proxy default; no registry)"
  py scripts/eval_prophecy_hit_rate_v1.py --run-mode proxy
  if ($LASTEXITCODE -ne 0) { throw "eval_prophecy_hit_rate exit $LASTEXITCODE" }
}

Write-Host "OK: B-Track daily hypothesis chain finished. Bundle: docs/final/artifacts/btrack_llm_input_bundle_latest.json"
