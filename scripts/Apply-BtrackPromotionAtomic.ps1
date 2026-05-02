<#
.SYNOPSIS
  Atomically apply B-track promotion candidate with rollback safety.

.DESCRIPTION
  Flow:
    1) Validate proposal is PENDING_APPROVAL + PROPOSE_PROMOTION.
    2) Backup current SSOT artifacts to a timestamped backup dir.
    3) Apply selected candidate report to btrack_quality_latest.json.
    4) Rebuild promotion gate + signoff packet.
    5) On failure, rollback from backup.

  This script does NOT touch Track A trading/runtime paths.

.PARAMETER ProposalPath
  Auto-Scientist proposal JSON path.

.PARAMETER BackupRoot
  Backup root directory for atomic promotion snapshots.

.PARAMETER Force
  Allow apply even if proposal is not pending approval.

.PARAMETER DryRun
  Print planned actions only.
#>
param(
    [string]$ProposalPath = "C:\workspace\reports\constitution\btrack_pilot\auto_scientist\promotion_proposal_v1_latest.json",
    [string]$ControlTowerPath = "C:\workspace\docs\final\artifacts\control_tower_latest.json",
    [string]$PreflightScriptPath = "C:\workspace\scripts\run_btrack_promotion_preflight_v1.py",
    [string]$PreflightOutPath = "C:\workspace\docs\final\artifacts\promotion_preflight_v1_latest.json",
    [string]$BackupRoot = "C:\workspace\reports\constitution\btrack_pilot\auto_scientist\promotion_backups",
    [int]$MaxPreflightAgeMinutes = 30,
    [int]$MaxControlTowerAgeMinutes = 30,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
Set-Location -LiteralPath $workspaceRoot

$qualityLatest = "C:\workspace\reports\constitution\btrack_pilot\btrack_quality_latest.json"
$gateLatest = "C:\workspace\reports\constitution\btrack_pilot\btrack_promotion_gate_latest.json"
$signoffLatest = "C:\workspace\docs\final\artifacts\btrack_promotion_signoff_packet_v1_latest.json"
$receiptLatest = "C:\workspace\reports\constitution\btrack_pilot\auto_scientist\promotion_apply_receipt_latest.json"

if (-not (Test-Path -LiteralPath $ProposalPath)) {
    throw "Proposal not found: $ProposalPath"
}

$proposal = Get-Content -LiteralPath $ProposalPath -Raw | ConvertFrom-Json
$status = [string]$proposal.status
$decision = [string]$proposal.decision_recommendation
$selectedCandidate = [string]$proposal.candidate_selection.selected_candidate_report
$readiness = ""
$readinessReasons = ""
if (Test-Path -LiteralPath $ControlTowerPath) {
    try {
        $ctObj = Get-Content -LiteralPath $ControlTowerPath -Raw | ConvertFrom-Json
        if ($null -ne $ctObj.promotion_readiness -and $null -ne $ctObj.promotion_readiness.status) {
            $readiness = [string]$ctObj.promotion_readiness.status
        }
        if ($null -ne $ctObj.promotion_readiness -and $null -ne $ctObj.promotion_readiness.reasons) {
            $readinessReasons = (($ctObj.promotion_readiness.reasons | ForEach-Object { [string]$_ }) -join ",")
        }
    } catch {
        throw "Failed to parse control tower readiness: $ControlTowerPath"
    }
}

if ([string]::IsNullOrWhiteSpace($selectedCandidate)) {
    throw "Proposal missing candidate_selection.selected_candidate_report"
}

if (-not (Test-Path -LiteralPath $selectedCandidate)) {
    throw "Selected candidate report not found: $selectedCandidate"
}

if (-not $Force) {
    if (-not (Test-Path -LiteralPath $PreflightScriptPath)) {
        throw "Preflight script not found: $PreflightScriptPath"
    }
    & py -u $PreflightScriptPath --proposal $ProposalPath --control-tower $ControlTowerPath --out $PreflightOutPath
    if ($LASTEXITCODE -ne 0) {
        throw "Promotion preflight failed. See: $PreflightOutPath"
    }
    if (-not (Test-Path -LiteralPath $PreflightOutPath)) {
        throw "Preflight output missing: $PreflightOutPath"
    }
    $preflightObj = Get-Content -LiteralPath $PreflightOutPath -Raw | ConvertFrom-Json
    if ([string]$preflightObj.result -ne "PASS") {
        throw "Preflight result is not PASS (result=$($preflightObj.result))."
    }
    if ($null -ne $preflightObj.generated_at_utc -and -not [string]::IsNullOrWhiteSpace([string]$preflightObj.generated_at_utc)) {
        $preflightTs = [DateTime]::Parse([string]$preflightObj.generated_at_utc).ToUniversalTime()
        $ageMin = ((Get-Date).ToUniversalTime() - $preflightTs).TotalMinutes
        if ($ageMin -gt $MaxPreflightAgeMinutes) {
            throw "Preflight is stale (${ageMin:N1}m > ${MaxPreflightAgeMinutes}m). Re-run control tower first."
        }
    }
    if ($null -ne $preflightObj.checks -and $null -ne $preflightObj.checks.selected_candidate_report) {
        $preflightCandidate = [string]$preflightObj.checks.selected_candidate_report
        if (-not [string]::IsNullOrWhiteSpace($preflightCandidate) -and $preflightCandidate -ne $selectedCandidate) {
            throw "Preflight selected candidate differs from proposal candidate. preflight=$preflightCandidate proposal=$selectedCandidate"
        }
    }
    if ($status -ne "PENDING_APPROVAL" -or $decision -ne "PROPOSE_PROMOTION") {
        throw "Proposal is not approvable (status=$status, decision=$decision). Use -Force to override."
    }
    if ($readiness -ne "GO_READY") {
        $reasonText = if ([string]::IsNullOrWhiteSpace($readinessReasons)) { "readiness status is $readiness" } else { $readinessReasons }
        throw "Promotion readiness gate failed: $reasonText. Use -Force to override."
    }
    if (Test-Path -LiteralPath $ControlTowerPath) {
        $ctFreshnessObj = Get-Content -LiteralPath $ControlTowerPath -Raw | ConvertFrom-Json
        if ($null -ne $ctFreshnessObj.generated_at_utc -and -not [string]::IsNullOrWhiteSpace([string]$ctFreshnessObj.generated_at_utc)) {
            $ctTs = [DateTime]::Parse([string]$ctFreshnessObj.generated_at_utc).ToUniversalTime()
            $ctAgeMin = ((Get-Date).ToUniversalTime() - $ctTs).TotalMinutes
            if ($ctAgeMin -gt $MaxControlTowerAgeMinutes) {
                throw "Control tower artifact is stale (${ctAgeMin:N1}m > ${MaxControlTowerAgeMinutes}m). Re-run control tower first."
            }
        }
    }
}

$ts = (Get-Date).ToUniversalTime().ToString("yyyyMMddHHmmss")
$backupDir = Join-Path $BackupRoot ("apply_" + $ts)
$backupQuality = Join-Path $backupDir "btrack_quality_latest.json"
$backupGate = Join-Path $backupDir "btrack_promotion_gate_latest.json"
$backupSignoff = Join-Path $backupDir "btrack_promotion_signoff_packet_v1_latest.json"

Write-Host "[atomic-apply] proposal: $ProposalPath" -ForegroundColor Cyan
Write-Host "[atomic-apply] selected candidate: $selectedCandidate" -ForegroundColor Cyan
Write-Host "[atomic-apply] promotion_readiness: $readiness" -ForegroundColor Cyan
Write-Host "[atomic-apply] backup dir: $backupDir" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "[atomic-apply] DryRun only. No files changed." -ForegroundColor Yellow
    exit 0
}

New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

if (Test-Path -LiteralPath $qualityLatest) { Copy-Item -LiteralPath $qualityLatest -Destination $backupQuality -Force }
if (Test-Path -LiteralPath $gateLatest) { Copy-Item -LiteralPath $gateLatest -Destination $backupGate -Force }
if (Test-Path -LiteralPath $signoffLatest) { Copy-Item -LiteralPath $signoffLatest -Destination $backupSignoff -Force }

$applied = $false
try {
    # Apply candidate as the new latest quality SSOT.
    Copy-Item -LiteralPath $selectedCandidate -Destination $qualityLatest -Force
    $applied = $true

    # Rebuild dependent gate artifacts.
    & py "scripts/evaluate_btrack_promotion_gate.py" --report $qualityLatest --out $gateLatest
    if ($LASTEXITCODE -ne 0) {
        throw "evaluate_btrack_promotion_gate.py failed rc=$LASTEXITCODE"
    }

    & py "scripts/build_btrack_promotion_signoff_packet_v1.py" --separate-track-gates
    if ($LASTEXITCODE -ne 0) {
        throw "build_btrack_promotion_signoff_packet_v1.py failed rc=$LASTEXITCODE"
    }

    $receipt = @{
        schema = "btrack_promotion_apply_receipt_v1"
        applied_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        proposal_path = $ProposalPath
        proposal_status = $status
        proposal_decision_recommendation = $decision
        promotion_readiness = $readiness
        promotion_readiness_reasons = $readinessReasons
        selected_candidate_report = $selectedCandidate
        target_quality_latest = $qualityLatest
        rebuilt_gate_latest = $gateLatest
        rebuilt_signoff_latest = $signoffLatest
        backup_dir = $backupDir
        rollback_performed = $false
        apply_result = "success"
    }
    ($receipt | ConvertTo-Json -Depth 6) + "`n" | Set-Content -LiteralPath $receiptLatest -Encoding UTF8
    Write-Host "[atomic-apply] SUCCESS" -ForegroundColor Green
    Write-Host "[atomic-apply] receipt: $receiptLatest" -ForegroundColor Green
    exit 0
}
catch {
    $err = $_.Exception.Message
    Write-Host "[atomic-apply] ERROR: $err" -ForegroundColor Red
    if ($applied) {
        Write-Host "[atomic-apply] rollback starting..." -ForegroundColor Yellow
        if (Test-Path -LiteralPath $backupQuality) { Copy-Item -LiteralPath $backupQuality -Destination $qualityLatest -Force }
        if (Test-Path -LiteralPath $backupGate) { Copy-Item -LiteralPath $backupGate -Destination $gateLatest -Force }
        if (Test-Path -LiteralPath $backupSignoff) { Copy-Item -LiteralPath $backupSignoff -Destination $signoffLatest -Force }
        Write-Host "[atomic-apply] rollback complete." -ForegroundColor Yellow
    }

    $receipt = @{
        schema = "btrack_promotion_apply_receipt_v1"
        applied_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        proposal_path = $ProposalPath
        proposal_status = $status
        proposal_decision_recommendation = $decision
        promotion_readiness = $readiness
        promotion_readiness_reasons = $readinessReasons
        selected_candidate_report = $selectedCandidate
        target_quality_latest = $qualityLatest
        rebuilt_gate_latest = $gateLatest
        rebuilt_signoff_latest = $signoffLatest
        backup_dir = $backupDir
        rollback_performed = $true
        apply_result = "failed"
        error = $err
    }
    ($receipt | ConvertTo-Json -Depth 6) + "`n" | Set-Content -LiteralPath $receiptLatest -Encoding UTF8
    exit 1
}

