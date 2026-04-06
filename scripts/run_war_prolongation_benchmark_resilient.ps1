<#
.SYNOPSIS
  Resilient runner for war-prolongation benchmark chain.

.DESCRIPTION
  Runs the benchmark chain with retry/backoff so transient errors do not stop progress.
  Writes a run log JSON each attempt and exits non-zero only after all retries fail.
#>
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [int]$MaxAttempts = 3,
  [int]$BackoffSeconds = 20,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if ($MaxAttempts -lt 1) { throw "MaxAttempts must be >= 1" }
if ($BackoffSeconds -lt 0) { throw "BackoffSeconds must be >= 0" }

$artifactDir = Join-Path $WorkspaceRoot "docs/final/artifacts"
if (-not (Test-Path -LiteralPath $artifactDir)) {
  New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
}

function Write-RunLog {
  param(
    [int]$Attempt,
    [string]$Status,
    [string]$Message,
    [int]$ExitCode
  )
  $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $obj = [ordered]@{
    schema = "war_prolongation_resilient_run_log_v1"
    generated_at_utc = $ts
    attempt = $Attempt
    status = $Status
    message = $Message
    exit_code = $ExitCode
    dry_run = [bool]$DryRun
    chain_script = "scripts/run_war_prolongation_benchmark_chain.ps1"
  }
  $path = Join-Path $artifactDir "war_prolongation_resilient_run_latest.json"
  $obj | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $path -Encoding UTF8
}

if ($DryRun) {
  Write-Host "DRY-RUN: resilience wrapper configured." -ForegroundColor Yellow
  Write-RunLog -Attempt 0 -Status "dry_run" -Message "No chain execution. Parameters validated." -ExitCode 0
  exit 0
}

for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
  Write-Host ("==== resilient run attempt {0}/{1} ====" -f $attempt, $MaxAttempts) -ForegroundColor Cyan
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts/run_war_prolongation_benchmark_chain.ps1")
  $ec = $LASTEXITCODE

  if ($ec -eq 0) {
    Write-RunLog -Attempt $attempt -Status "ok" -Message "Chain completed successfully." -ExitCode 0
    Write-Host "OK: resilient benchmark run completed." -ForegroundColor Green
    exit 0
  }

  Write-RunLog -Attempt $attempt -Status "failed_attempt" -Message ("Chain failed at attempt {0}" -f $attempt) -ExitCode $ec
  if ($attempt -lt $MaxAttempts) {
    Write-Warning ("Attempt {0} failed (exit {1}). Retrying in {2}s..." -f $attempt, $ec, $BackoffSeconds)
    if ($BackoffSeconds -gt 0) {
      Start-Sleep -Seconds $BackoffSeconds
    }
  }
}

Write-RunLog -Attempt $MaxAttempts -Status "failed_final" -Message "All resilient attempts exhausted." -ExitCode 1
throw "Resilient chain failed after $MaxAttempts attempts."

