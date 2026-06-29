# Human gate: interactive approve -> intake + provenance -> optional auto intake + n30 sync.
param(
    [Parameter(Mandatory = $true)]
    [string]$TenantId,
    [Parameter(Mandatory = $true)]
    [string]$SourceJsonl,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$HumanVerifiedBy = "commander",
    [string]$ConsentSourceRef = "",
    [string]$ConsentType = "email",
    [switch]$ApproveAll,
    [switch]$SyncEnrollment,
    [switch]$TriggerIntake,
    [switch]$PublicFacingOk,
    [int]$MinApprove = 20,
    [ValidateSet("customer_masked", "operator_panel")]
    [string]$Lane = "customer_masked",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

if ($ConsentSourceRef -eq "") {
    $ConsentSourceRef = "data/wtt/provenance/evidence/${TenantId}_consent.txt"
}

Write-Host "=== WTT Human Gate Routine ===" -ForegroundColor Cyan
Write-Host "SEND HOLD | provenance required before drop-watch auto intake" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "[DryRun] human gate -> provenance check -> optional intake" -ForegroundColor DarkGray
    exit 0
}

$gateArgs = @(
    "scripts/run_wtt_human_gate_interactive_v1.py",
    "--tenant-id", $TenantId,
    "--source-jsonl", $SourceJsonl,
    "--human-verified-by", $HumanVerifiedBy,
    "--consent-type", $ConsentType,
    "--consent-source-ref", $ConsentSourceRef,
    "--min-approve", "$MinApprove",
    "--lane", $Lane
)
if ($ApproveAll) { $gateArgs += "--approve-all" }
if ($SyncEnrollment) { $gateArgs += "--sync-enrollment" }
if ($TriggerIntake) { $gateArgs += "--trigger-intake" }
if ($PublicFacingOk) { $gateArgs += "--public-facing-ok" }

& py @gateArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($SyncEnrollment) {
    & py scripts/check_wtt_human_n30_gate_v1.py --sync-pack
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "OK human gate | intake: data/wtt/intake/${TenantId}.jsonl" -ForegroundColor Green
Write-Host "OK provenance: data/wtt/provenance/${TenantId}.provenance.json" -ForegroundColor Green
exit 0
