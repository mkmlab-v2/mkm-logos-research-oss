# One-click: auto materialize 20–30 row masked JSONL + customer pilot intake (SEND_GATE HOLD).
# Synthetic local only — NOT real customer data; customer_provided stays false.

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TenantId = "wtt-premium-cs-auto-local-v1",
    [int]$Sessions = 30,
    [int]$MaxCases = 30,
    [switch]$SkipMaterialize,
    [switch]$SkipIntake,
    [switch]$DryRun,
    [switch]$BtrackCsShortContext = $true,
    [switch]$NoBtrackCsShortContext,
    [switch]$StrictPassGate
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$OutJsonl = Join-Path $WorkspaceRoot "data\wtt\intake\wtt-premium-cs-auto-local-v1.local.jsonl"
$relOut = "data\wtt\intake\wtt-premium-cs-auto-local-v1.local.jsonl"

if ($Sessions -lt 20 -or $Sessions -gt 30) {
    Write-Error "Sessions must be 20–30 (got $Sessions)."
}

$useBtrack = $BtrackCsShortContext -and -not $NoBtrackCsShortContext

Write-Host "=== Compression customer pilot AUTO LOCAL ===" -ForegroundColor Cyan
Write-Host "tenant: $TenantId | sessions: $Sessions | synthetic masked | SEND_GATE HOLD" -ForegroundColor Yellow
Write-Host "NOT real customer data — customer_provided=false [HYPO]/research_only" -ForegroundColor DarkYellow

if ($DryRun) {
    Write-Host "[DryRun] materialize -> intake (BtrackCsShortContext=$useBtrack)" -ForegroundColor DarkGray
    exit 0
}

if (-not $SkipMaterialize) {
    Write-Host "=== Step 1/3: materialize masked JSONL ===" -ForegroundColor Cyan
    & py scripts/materialize_wtt_premium_cs_auto_local_v1.py --sessions $Sessions --out-jsonl $OutJsonl
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    if (-not (Test-Path -LiteralPath $OutJsonl)) {
        Write-Error "SkipMaterialize but missing: $OutJsonl"
    }
    Write-Host "=== Step 1/3: skip materialize (existing file) ===" -ForegroundColor DarkGray
}

Write-Host "=== Step 2/3: validate JSONL schema ===" -ForegroundColor Cyan
& py scripts/validate_wtt_pilot_jsonl_v1.py --jsonl $relOut --min-sessions 20 --strict
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($SkipIntake) {
    Write-Host "=== Step 3/3: skip intake (-SkipIntake) ===" -ForegroundColor DarkGray
    Write-Host "Done. JSONL: $relOut" -ForegroundColor Green
    exit 0
}

Write-Host "=== Step 3/3: customer pilot intake chain ===" -ForegroundColor Cyan
$intakeArgs = @(
    "-TenantId", $TenantId,
    "-CustomerJsonl", $relOut,
    "-MaxCases", "$MaxCases",
    "-MinCases", "20"
)
if ($useBtrack) { $intakeArgs += "-BtrackCsShortContext" }
if ($StrictPassGate) { $intakeArgs += "-StrictPassGate" }

& powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-CompressionCustomerPilotIntake_v1.ps1 @intakeArgs
exit $LASTEXITCODE
