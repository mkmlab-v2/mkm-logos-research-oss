#Requires -Version 5.1
<#
.SYNOPSIS
  권장 방안 번들: ops 리포트 갱신 + overnight/regime 실험 + neutral cohort (research only).
#>
param([string]$WorkspaceRoot = "C:\workspace")

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

& py scripts\build_btrack_ensemble_per_date_directions_v1.py --recent-trading-days 30
if ($LASTEXITCODE -ne 0) { throw "per-date exit $LASTEXITCODE" }

& py scripts\build_btrack_headline_miss_report_v1.py
& py scripts\build_btrack_wrong_direction_lens_report_v1.py
& py scripts\build_btrack_neutral_abstain_cohort_report_v1.py
if ($LASTEXITCODE -ne 0) { throw "neutral cohort exit $LASTEXITCODE" }

& py scripts\run_btrack_overnight_regime_experiment_v1.py
if ($LASTEXITCODE -ne 0) { throw "overnight regime experiment exit $LASTEXITCODE" }

& py scripts\run_btrack_candidate_oos_180d_v1.py
if ($LASTEXITCODE -ne 0) { throw "candidate OOS 180d exit $LASTEXITCODE" }

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-BtrackRfcF2F3Research_v1.ps1 -WorkspaceRoot $WorkspaceRoot
if ($LASTEXITCODE -ne 0) { throw "RFC F2/F3 research exit $LASTEXITCODE" }

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-BtrackConditionalGateMatrix_v1.ps1 -WorkspaceRoot $WorkspaceRoot
if ($LASTEXITCODE -ne 0) { throw "conditional gate matrix exit $LASTEXITCODE" }

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-BtrackWrongDirHoldout_v1.ps1 -WorkspaceRoot $WorkspaceRoot
if ($LASTEXITCODE -ne 0) { throw "wrong_dir holdout full exit $LASTEXITCODE" }

Write-Host "[OK] B-track recommended research bundle complete" -ForegroundColor Green
Write-Host "Ops: ALERT_1b + reports/*_latest.json; production btrack_lens_ensemble_v1.json unchanged." -ForegroundColor DarkGray
