<#
.SYNOPSIS
  Run stable/exploratory symbol lane pipelines and compare C queues.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_symbol_lane_dual_compare.ps1
#>
param()

$ErrorActionPreference = 'Stop'

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$stable = Join-Path $workspaceRoot 'scripts\run_symbol_lane_stable.ps1'
$expl = Join-Path $workspaceRoot 'scripts\run_symbol_lane_exploratory.ps1'
$compare = Join-Path $workspaceRoot 'scripts\report_symbol_c_queue_compare.py'
$checklist = Join-Path $workspaceRoot 'scripts\build_symbol_c_validation_checklist.py'
$packet = Join-Path $workspaceRoot 'scripts\build_symbol_c_validation_packet.py'
$packetGate = Join-Path $workspaceRoot 'scripts\check_symbol_c_validation_packet.py'
$packetLock = Join-Path $workspaceRoot 'scripts\lock_symbol_c_validation_packet_baseline.py'
$packetRegression = Join-Path $workspaceRoot 'scripts\check_symbol_c_validation_packet_regression.py'
$packetArchive = Join-Path $workspaceRoot 'scripts\archive_symbol_c_validation_run.py'
$packetPrune = Join-Path $workspaceRoot 'scripts\prune_symbol_c_validation_history.py'
$packetIndex = Join-Path $workspaceRoot 'scripts\update_symbol_c_validation_run_index.py'
$packetIndexAlert = Join-Path $workspaceRoot 'scripts\check_symbol_c_validation_run_index_alert.py'
$packetIndexWarn = Join-Path $workspaceRoot 'scripts\warn_symbol_c_validation_run_index_alert.py'
$packetWarnFlag = Join-Path $workspaceRoot 'scripts\emit_symbol_c_validation_warning_flag.py'
$packetDeltaPrune = Join-Path $workspaceRoot 'scripts\prune_symbol_c_delta_alert_logs.py'
$retentionTemplateDev = Join-Path $workspaceRoot 'data\logos\btrack_pilot\gates\symbol_c_validation_delta_log_retention_template_dev.json'
$retentionTemplateProd = Join-Path $workspaceRoot 'data\logos\btrack_pilot\gates\symbol_c_validation_delta_log_retention_template_prod.json'
$historyRetentionTemplateDev = Join-Path $workspaceRoot 'data\logos\btrack_pilot\gates\symbol_c_validation_history_retention_template_dev.json'
$historyRetentionTemplateProd = Join-Path $workspaceRoot 'data\logos\btrack_pilot\gates\symbol_c_validation_history_retention_template_prod.json'

foreach ($p in @($stable, $expl, $compare, $checklist, $packet, $packetGate, $packetLock, $packetRegression, $packetArchive, $packetPrune, $packetIndex, $packetIndexAlert, $packetIndexWarn, $packetWarnFlag, $packetDeltaPrune)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Required file not found: $p"
    }
}

$retentionMode = $env:SYMBOL_C_RETENTION_ENV
if ([string]::IsNullOrWhiteSpace($retentionMode)) { $retentionMode = 'prod' }
$retentionMode = $retentionMode.ToLowerInvariant()
$retentionDryRun = $false
if (($env:SYMBOL_C_RETENTION_DRY_RUN -eq '1') -or ($env:SYMBOL_C_RETENTION_DRY_RUN -eq 'true')) { $retentionDryRun = $true }
$retentionTemplate = $retentionTemplateProd
if ($retentionMode -eq 'dev') { $retentionTemplate = $retentionTemplateDev }
$historyRetentionTemplate = $historyRetentionTemplateProd
if ($retentionMode -eq 'dev') { $historyRetentionTemplate = $historyRetentionTemplateDev }
Write-Host ("== Symbol Lane Bundle: retention mode = {0} ==" -f $retentionMode) -ForegroundColor DarkCyan
Write-Host ("== Symbol Lane Bundle: retention dry-run = {0} ==" -f $retentionDryRun) -ForegroundColor DarkCyan

Set-Location -LiteralPath $workspaceRoot

Write-Host '== Symbol Lane Bundle: stable ==' -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File $stable
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: exploratory ==' -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File $expl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: C queue compare ==' -ForegroundColor Cyan
& py $compare
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: C checklist (stable) ==' -ForegroundColor Cyan
& py $checklist --in-jsonl (Join-Path $workspaceRoot 'reports\constitution\btrack_pilot\symbol_c_validation_queue_stable_latest.jsonl') --out-json (Join-Path $workspaceRoot 'reports\constitution\btrack_pilot\symbol_c_validation_checklist_stable_latest.json')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: C checklist (exploratory) ==' -ForegroundColor Cyan
& py $checklist --in-jsonl (Join-Path $workspaceRoot 'reports\constitution\btrack_pilot\symbol_c_validation_queue_exploratory_latest.jsonl') --out-json (Join-Path $workspaceRoot 'reports\constitution\btrack_pilot\symbol_c_validation_checklist_exploratory_latest.json')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: C validation packet ==' -ForegroundColor Cyan
& py $packet
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: C validation packet gate ==' -ForegroundColor Cyan
& py $packetGate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: C validation packet baseline lock ==' -ForegroundColor Cyan
& py $packetLock
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: C validation packet regression ==' -ForegroundColor Cyan
& py $packetRegression
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: C validation packet archive ==' -ForegroundColor Cyan
& py $packetArchive
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: C validation history prune ==' -ForegroundColor Cyan
if ($retentionDryRun) {
  & py $packetPrune --retention-template $historyRetentionTemplate --dry-run
} else {
  & py $packetPrune --retention-template $historyRetentionTemplate
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: C validation run index ==' -ForegroundColor Cyan
& py $packetIndex
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: C validation run index alert ==' -ForegroundColor Cyan
& py $packetIndexAlert
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: C validation run index strict warn ==' -ForegroundColor Cyan
& py $packetIndexWarn --alert-profile strict --delta-alert-log-rotate-daily
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: C validation warning flag ==' -ForegroundColor Cyan
& py $packetWarnFlag --alert-profile strict
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '== Symbol Lane Bundle: Delta alert log prune ==' -ForegroundColor Cyan
if ($retentionDryRun) {
  & py $packetDeltaPrune --retention-template $retentionTemplate --dry-run
} else {
  & py $packetDeltaPrune --retention-template $retentionTemplate
}
exit $LASTEXITCODE
