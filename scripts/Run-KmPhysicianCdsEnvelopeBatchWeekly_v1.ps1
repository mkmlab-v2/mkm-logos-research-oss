#Requires -Version 5.1
<#
.SYNOPSIS
  KM 의사 CDS assist envelope JSONL 배치 산출 갱신 (스키마 검증 포함; LLM 없음).

.DESCRIPTION
  scripts/run_km_physician_cds_assist_envelope_batch_v1.py 실행.
  기본 입력: tests/fixtures/km_physician_cds_assist_payload_batch_v1.example.jsonl (데모 페이로드).
  기본 출력: reports/km_physician_cds_envelope_batch_latest.jsonl

.PARAMETER AllowPartial
  일부 행 실패 시에도 exit 0 (--allow-partial).

.EXAMPLE
  pwsh -File scripts/Run-KmPhysicianCdsEnvelopeBatchWeekly_v1.ps1

.EXAMPLE
  pwsh -File scripts/Run-KmPhysicianCdsEnvelopeBatchWeekly_v1.ps1 -InputJsonl "C:\path\to\payloads.jsonl"
#>
param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$InputJsonl = "",
    [string]$OutputJsonl = "",
    [switch]$AllowPartial,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$batch = Join-Path $WorkspaceRoot "scripts\run_km_physician_cds_assist_envelope_batch_v1.py"
if (-not (Test-Path -LiteralPath $batch)) {
    throw "Missing batch script: $batch"
}

if ([string]::IsNullOrWhiteSpace($InputJsonl)) {
    $InputJsonl = Join-Path $WorkspaceRoot "tests\fixtures\km_physician_cds_assist_payload_batch_v1.example.jsonl"
}
if ([string]::IsNullOrWhiteSpace($OutputJsonl)) {
    $OutputJsonl = Join-Path $WorkspaceRoot "reports\km_physician_cds_envelope_batch_latest.jsonl"
}

if (-not (Test-Path -LiteralPath $InputJsonl)) {
    throw "Input JSONL not found: $InputJsonl"
}

$argsList = @(
    $batch,
    "--in", $InputJsonl,
    "--out", $OutputJsonl
)
if ($DryRun) { $argsList += "--dry-run" }
if ($AllowPartial) { $argsList += "--allow-partial" }

& py @argsList
exit $LASTEXITCODE
