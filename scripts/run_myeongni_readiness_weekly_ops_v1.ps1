param(
  [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot/..")

$ts = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"

# 1) No-backfill weekly observation refresh.
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run_myeongni_shadow_monthly_catchup_v1.ps1"

# 2) Sensitivity sweep + freeze evidence.
py "scripts/run_myeongni_readiness_freeze_and_sensitivity.py"

# 3) Optional focused regressions.
if (-not $SkipPytest) {
  py -m pytest "tests/test_build_myeongni_commercialization_readiness_packet.py" "tests/test_independent_lens_shadow_gate_v1.py" -q
}

# 3.5) Ensure canonical readiness packet threshold after tests.
py "scripts/build_myeongni_commercialization_readiness_packet.py" --max-shadow-override-ratio 0.01

# 4) Append lightweight weekly log row.
$packetPath = "docs/final/artifacts/myeongni_commercialization_readiness_packet_latest.json"
$reportPath = "docs/final/artifacts/myeongni_readiness_sensitivity_report_latest.json"
$logPath = "reports/myeongni_readiness_weekly_log.jsonl"

$packet = Get-Content -Raw $packetPath | ConvertFrom-Json
$report = Get-Content -Raw $reportPath | ConvertFrom-Json

$row = [ordered]@{
  ts_local = $ts
  readiness = $packet.readiness
  shadow_override_ratio = $packet.summary.shadow_override_ratio
  shadow_override_ratio_limit = $packet.summary.shadow_override_ratio_limit
  shadow_override_ratio_exceeded = $packet.summary.shadow_override_ratio_exceeded
  fusion_agreement_rate = $packet.summary.fusion_agreement_rate
  shadow_blockers_count = $packet.summary.shadow_blockers_count
  freeze_dir = $report.freeze_dir
}

New-Item -ItemType Directory -Force -Path "reports" | Out-Null
($row | ConvertTo-Json -Compress) | Out-File -FilePath $logPath -Append -Encoding utf8

Write-Host "DONE: run_myeongni_readiness_weekly_ops_v1"
