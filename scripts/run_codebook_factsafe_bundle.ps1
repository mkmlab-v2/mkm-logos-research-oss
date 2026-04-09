<#
.SYNOPSIS
  Run fact-safe codebook validation bundle.

.DESCRIPTION
  Executes a minimal, reproducible local bundle for codebook-related paths:
  1) validate_master_codebook_schema.py
  2) validate_master_codebook_real_samples.py
  3) run_master_codebook_training_smoke.py
  4) l1_codebook_bypass.py
  5) run_prophecy_micro_codebook_poc.py

  Writes a compact result artifact to:
  docs/final/artifacts/codebook_factsafe_bundle_latest.json

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_codebook_factsafe_bundle.ps1
#>
param(
    [int]$SmokeCount = 500,
    [string]$SmokePrefix = "bundle_probe",
    [switch]$SkipMicroPoc,
    [switch]$IncludeRecoveredReadiness
)

$ErrorActionPreference = 'Stop'

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$artifactPath = Join-Path $workspaceRoot 'docs\final\artifacts\codebook_factsafe_bundle_latest.json'

Set-Location -LiteralPath $workspaceRoot

$steps = @(
    @{
        id = 'validate_schema'
        cmd = @('py', 'scripts/validate_master_codebook_schema.py')
    },
    @{
        id = 'validate_real_samples'
        cmd = @('py', 'scripts/validate_master_codebook_real_samples.py')
    },
    @{
        id = 'training_smoke'
        cmd = @('py', 'scripts/run_master_codebook_training_smoke.py', '--count', "$SmokeCount", '--prefix', $SmokePrefix)
    },
    @{
        id = 'l1_bypass_poc'
        cmd = @('py', 'scripts/l1_codebook_bypass.py')
    }
)

if (-not $SkipMicroPoc) {
    $steps += @{
        id = 'prophecy_micro_codebook_poc'
        cmd = @('py', 'scripts/run_prophecy_micro_codebook_poc.py')
    }
}

$results = @()
$overallStart = Get-Date

foreach ($step in $steps) {
    $stepStart = Get-Date
    $id = $step.id
    $cmd = $step.cmd
    Write-Host "== Codebook Fact-Safe: $id ==" -ForegroundColor Cyan

    & $cmd[0] $cmd[1..($cmd.Length - 1)]
    $exitCode = $LASTEXITCODE
    $elapsedMs = [int]((Get-Date) - $stepStart).TotalMilliseconds

    $results += [ordered]@{
        id = $id
        exit_code = $exitCode
        elapsed_ms = $elapsedMs
        command = ($cmd -join ' ')
    }

    if ($exitCode -ne 0) {
        $payload = [ordered]@{
            schema = 'codebook_factsafe_bundle_v1'
            generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            ok = $false
            failed_step = $id
            steps = $results
            elapsed_ms_total = [int]((Get-Date) - $overallStart).TotalMilliseconds
        }
        $json = $payload | ConvertTo-Json -Depth 6
        $artifactDir = Split-Path -Parent $artifactPath
        New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
        Set-Content -LiteralPath $artifactPath -Value $json -Encoding UTF8
        exit $exitCode
    }
}

$recoveredReadiness = $null
if ($IncludeRecoveredReadiness) {
    $recoveredScript = Join-Path $workspaceRoot 'scripts\experimental\codepack_recovery\run_recovered_codebook_operational_readiness.py'
    if (-not (Test-Path -LiteralPath $recoveredScript)) {
        throw "Recovered readiness script not found: $recoveredScript"
    }
    Write-Host "== Codebook Fact-Safe: recovered_operational_readiness ==" -ForegroundColor Cyan
    & py $recoveredScript
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        $payload = [ordered]@{
            schema = 'codebook_factsafe_bundle_v1'
            generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            ok = $false
            failed_step = 'recovered_operational_readiness'
            steps = $results
            recovered_readiness = [ordered]@{
                included = $true
                exit_code = $exitCode
            }
            elapsed_ms_total = [int]((Get-Date) - $overallStart).TotalMilliseconds
        }
        $json = $payload | ConvertTo-Json -Depth 6
        $artifactDir = Split-Path -Parent $artifactPath
        New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
        Set-Content -LiteralPath $artifactPath -Value $json -Encoding UTF8
        exit $exitCode
    }
    $recoveredReadiness = [ordered]@{
        included = $true
        exit_code = 0
        artifact = 'docs/final/artifacts/recovered_codebook_operational_readiness_latest.json'
    }
}

$okPayload = [ordered]@{
    schema = 'codebook_factsafe_bundle_v1'
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    ok = $true
    options = [ordered]@{
        smoke_count = $SmokeCount
        smoke_prefix = $SmokePrefix
        skip_micro_poc = [bool]$SkipMicroPoc
        include_recovered_readiness = [bool]$IncludeRecoveredReadiness
    }
    steps = $results
    outputs = [ordered]@{
        l1_bypass_artifact = 'docs/final/artifacts/l1_codebook_bypass_poc_latest.json'
        micro_codebook_artifact = 'docs/final/artifacts/prophecy_micro_codebook_poc_latest.json'
        smoke_marker_json = "reports/constitution/master_codebook_training_smoke_${SmokePrefix}_${SmokeCount}.json"
    }
    recovered_readiness = $recoveredReadiness
    elapsed_ms_total = [int]((Get-Date) - $overallStart).TotalMilliseconds
}

$okJson = $okPayload | ConvertTo-Json -Depth 6
$artifactDir = Split-Path -Parent $artifactPath
New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
Set-Content -LiteralPath $artifactPath -Value $okJson -Encoding UTF8

Write-Host "Bundle artifact: $artifactPath" -ForegroundColor Green
exit 0

