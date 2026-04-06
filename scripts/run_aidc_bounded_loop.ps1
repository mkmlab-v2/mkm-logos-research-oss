<#
.SYNOPSIS
  Run bounded AIDC experiment loop with strict stop gates.

.DESCRIPTION
  Executes an optional Cursor CLI review step and required AIDC artifact/gate steps.
  Hard stop conditions:
  - Iteration limit reached
  - Time budget exceeded
  - `docs/final/artifacts/aidc_kpi_gate.json` decision is `NO_GO`

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\run_aidc_bounded_loop.ps1" -MaxIterations 3 -TimeBudgetMinutes 90 -EnableStep1Review
#>
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [int]$MaxIterations = 3,
  [int]$TimeBudgetMinutes = 90,
  [switch]$EnableStep1Review,
  [switch]$SkipOfficialFactLockChain,
  [string]$AidcOutputSuffix = "_v2",
  [int]$SleepSecondsBetweenIterations = 0,
  [int]$Step2Iterations = 30
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if ($MaxIterations -lt 1) { throw "MaxIterations must be >= 1" }
if ($TimeBudgetMinutes -lt 1) { throw "TimeBudgetMinutes must be >= 1" }
if ($SleepSecondsBetweenIterations -lt 0) { throw "SleepSecondsBetweenIterations must be >= 0" }
if ($Step2Iterations -lt 1) { throw "Step2Iterations must be >= 1" }

$gateFileName = if ([string]::IsNullOrWhiteSpace($AidcOutputSuffix)) { "aidc_kpi_gate.json" } else { "aidc_kpi_gate$AidcOutputSuffix.json" }
$gatePath = Join-Path $WorkspaceRoot "docs/final/artifacts/$gateFileName"
$deadline = (Get-Date).AddMinutes($TimeBudgetMinutes)

function Invoke-Step1Review {
  $agentCmd = Get-Command agent -ErrorAction SilentlyContinue
  if (-not $agentCmd) {
    Write-Warning "Cursor CLI 'agent' command not found. Skipping Step 1 review."
    return
  }
  Write-Host "==> Step 1 (optional): Cursor CLI review" -ForegroundColor Cyan
  & agent -p "review current A/B benchmark changes for correctness, performance risks, and reproducibility gaps" --output-format text
  if ($LASTEXITCODE -ne 0) {
    throw "Step 1 review failed with exit code $LASTEXITCODE"
  }
}

function Invoke-Step2Aidc {
  if (-not $SkipOfficialFactLockChain) {
    Write-Host "==> Fact-Lock chain: design-equivalence -> metric generation -> interpretation" -ForegroundColor Cyan
    & py (Join-Path $WorkspaceRoot "scripts/run_p1_efficiency_ab.py") --profile balanced
    if ($LASTEXITCODE -ne 0) { throw "run_p1_efficiency_ab.py failed: $LASTEXITCODE" }

    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts/run_compression_automation_chain.ps1") -WorkspaceRoot $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) { throw "run_compression_automation_chain.ps1 failed: $LASTEXITCODE" }
  }

  Write-Host "==> Step 2 (required): build_btrack_prophecy_score_from_ohlcv.py" -ForegroundColor Cyan
  & py (Join-Path $WorkspaceRoot "scripts/build_btrack_prophecy_score_from_ohlcv.py")
  if ($LASTEXITCODE -ne 0) { throw "build_btrack_prophecy_score_from_ohlcv.py failed: $LASTEXITCODE" }

  Write-Host "==> Step 2 (required): refresh_aidc_ab_result_summary.py" -ForegroundColor Cyan
  & py (Join-Path $WorkspaceRoot "scripts/refresh_aidc_ab_result_summary.py")
  if ($LASTEXITCODE -ne 0) { throw "refresh_aidc_ab_result_summary.py failed: $LASTEXITCODE" }

  Write-Host "==> Step 2 (required): update_aidc_kpi_gate.py --label baseline --measurement-mode subprocess --output-suffix $AidcOutputSuffix" -ForegroundColor Cyan
  & py (Join-Path $WorkspaceRoot "scripts/update_aidc_kpi_gate.py") --label baseline --iterations $Step2Iterations --measurement-mode subprocess --output-suffix $AidcOutputSuffix
  if ($LASTEXITCODE -ne 0) { throw "update_aidc_kpi_gate.py baseline failed: $LASTEXITCODE" }

  Write-Host "==> Step 2 (required): update_aidc_kpi_gate.py --label treatment --measurement-mode subprocess --output-suffix $AidcOutputSuffix" -ForegroundColor Cyan
  & py (Join-Path $WorkspaceRoot "scripts/update_aidc_kpi_gate.py") --label treatment --iterations $Step2Iterations --measurement-mode subprocess --output-suffix $AidcOutputSuffix
  if ($LASTEXITCODE -ne 0) { throw "update_aidc_kpi_gate.py treatment failed: $LASTEXITCODE" }
}

function Read-GateDecision {
  if (-not (Test-Path -LiteralPath $gatePath)) {
    throw "Gate file not found: $gatePath"
  }
  $gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
  if (-not $gate.go_no_go -or -not $gate.go_no_go.decision) {
    throw "Invalid gate JSON format: missing go_no_go.decision"
  }
  return [string]$gate.go_no_go.decision
}

for ($i = 1; $i -le $MaxIterations; $i++) {
  if ((Get-Date) -gt $deadline) {
    throw "Time budget exceeded before iteration $i. Deadline: $deadline"
  }

  Write-Host ""
  Write-Host ("==== AIDC bounded loop iteration {0}/{1} ====" -f $i, $MaxIterations) -ForegroundColor Yellow

  if ($EnableStep1Review -and $i -eq 1) {
    Invoke-Step1Review
  }

  Invoke-Step2Aidc
  $decision = Read-GateDecision
  Write-Host ("Gate decision after iteration {0}: {1}" -f $i, $decision) -ForegroundColor Green

  if ($decision -eq "NO_GO") {
    throw "Hard stop: aidc_kpi_gate decision is NO_GO (iteration $i)."
  }

  if ($decision -eq "GO") {
    Write-Host "GO achieved. Loop finished early." -ForegroundColor Green
    exit 0
  }

  if ($i -lt $MaxIterations -and $SleepSecondsBetweenIterations -gt 0) {
    Start-Sleep -Seconds $SleepSecondsBetweenIterations
  }
}

Write-Host "Loop completed within configured bounds (no GO and no NO_GO hard-stop)." -ForegroundColor Yellow
exit 0
