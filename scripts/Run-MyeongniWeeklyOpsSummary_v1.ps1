<#
.SYNOPSIS
  Thin weekly ops index for Myeongni lens + independent-lens shadow gate (JSON SSOT only; this MD is not authoritative).

.DESCRIPTION
  Fact-Lock alignment (CONSTITUTION table: independent lens / fusion stub / shadow gate):
    1) scripts/run_lens_myeongni.py -> docs/final/artifacts/myeongni_independent_lens_latest.json
    2) scripts/report_independent_lens_fusion_stub_v0.py -> docs/final/artifacts/independent_lens_fusion_stub_latest.json
       (Shadow gate reads fusion; skipping this step usually makes the gate exit with missing fusion.)
    3) scripts/report_independent_lens_shadow_gate.py -> docs/final/artifacts/independent_lens_shadow_gate_latest.json
    4) Tail of reports/role_router_s1_shadow_advisory_log.jsonl (append-only; populated by build_role_router_s1_shadow_advisory_v1.py when run elsewhere)

  Output: reports/myeongni_weekly_ops_summary_latest.md (paths, filesystem mtimes, copied JSON fields only).

.PARAMETER DryRun
  Print planned commands and exit 0 without executing Python or writing the MD file.
#>
param(
    [string]$WorkspaceRoot = 'C:\workspace',
    [switch]$SkipLensRefresh,
    [switch]$SkipFusionStubRefresh,
    [switch]$SkipShadowGate,
    [switch]$SkipAdvisoryTail,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $root

$pyLens = @('scripts\run_lens_myeongni.py')
$pyFusion = @('scripts\report_independent_lens_fusion_stub_v0.py')
$pyGate = @('scripts\report_independent_lens_shadow_gate.py')

$pLens = Join-Path $root 'docs\final\artifacts\myeongni_independent_lens_latest.json'
$pFusion = Join-Path $root 'docs\final\artifacts\independent_lens_fusion_stub_latest.json'
$pGate = Join-Path $root 'docs\final\artifacts\independent_lens_shadow_gate_latest.json'
$pAdvisoryLog = Join-Path $root 'reports\role_router_s1_shadow_advisory_log.jsonl'
$outMd = Join-Path $root 'reports\myeongni_weekly_ops_summary_latest.md'

function Get-FileMtimeUtc([string]$LiteralPath) {
    if (-not (Test-Path -LiteralPath $LiteralPath)) { return $null }
    return (Get-Item -LiteralPath $LiteralPath).LastWriteTimeUtc.ToString('yyyy-MM-ddTHH:mm:ssZ')
}

function Read-JsonFile([string]$LiteralPath) {
    if (-not (Test-Path -LiteralPath $LiteralPath)) { return $null }
    $raw = Get-Content -LiteralPath $LiteralPath -Raw -Encoding UTF8
    return $raw | ConvertFrom-Json
}

if ($DryRun) {
    Write-Host 'DRY RUN - planned sequence:' -ForegroundColor Cyan
    if (-not $SkipLensRefresh) { Write-Host ('  py ' + ($pyLens -join ' ')) }
    if (-not $SkipFusionStubRefresh) { Write-Host ('  py ' + ($pyFusion -join ' ')) }
    if (-not $SkipShadowGate) { Write-Host ('  py ' + ($pyGate -join ' ')) }
    Write-Host "  -> write $outMd"
    exit 0
}

if (-not $SkipLensRefresh) {
    Write-Host '== (1) run_lens_myeongni.py ==' -ForegroundColor Cyan
    & py @pyLens
    if ($LASTEXITCODE -ne 0) { throw "run_lens_myeongni.py failed (exit $LASTEXITCODE)" }
}

if (-not $SkipFusionStubRefresh) {
    Write-Host '== (2) report_independent_lens_fusion_stub_v0.py (gate prerequisite) ==' -ForegroundColor Cyan
    & py @pyFusion
    if ($LASTEXITCODE -ne 0) { throw "report_independent_lens_fusion_stub_v0.py failed (exit $LASTEXITCODE)" }
}

if (-not $SkipShadowGate) {
    Write-Host '== (3) report_independent_lens_shadow_gate.py ==' -ForegroundColor Cyan
    & py @pyGate
    if ($LASTEXITCODE -ne 0) { throw "report_independent_lens_shadow_gate.py failed (exit $LASTEXITCODE)" }
}

$generatedUtc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$lens = Read-JsonFile $pLens
$fusionDoc = Read-JsonFile $pFusion
$gate = Read-JsonFile $pGate

$advisoryLine = $null
if (-not $SkipAdvisoryTail -and (Test-Path -LiteralPath $pAdvisoryLog)) {
    $lines = Get-Content -LiteralPath $pAdvisoryLog -Encoding UTF8 | Where-Object { $_.Trim().Length -gt 0 }
    if ($lines.Count -gt 0) { $advisoryLine = $lines[$lines.Count - 1] }
}

$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine('# Myeongni weekly ops summary (wrapper index)')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('This file is a **non-authoritative index**. Decisions and metrics live in the JSON paths below (Fact-Lock).')
[void]$sb.AppendLine('')
[void]$sb.AppendLine("| Field | Value |")
[void]$sb.AppendLine("| --- | --- |")
[void]$sb.AppendLine("| generated_at_utc (this md) | ``$generatedUtc`` |")
[void]$sb.AppendLine('')
[void]$sb.AppendLine('## 1) Lens (Myeongni independent)')
[void]$sb.AppendLine('')
[void]$sb.AppendLine("| Key | Value |")
[void]$sb.AppendLine("| --- | --- |")
[void]$sb.AppendLine("| path | ``docs/final/artifacts/myeongni_independent_lens_latest.json`` |")
[void]$sb.AppendLine("| file_mtime_utc | ``$(Get-FileMtimeUtc $pLens)`` |")
if ($lens) {
    [void]$sb.AppendLine("| artifact ts_utc | ``$($lens.ts_utc)`` |")
    $ds = $lens.scores.direction_score
    if ($null -ne $ds) { [void]$sb.AppendLine("| scores.direction_score | ``$ds`` |") }
    [void]$sb.AppendLine("| schema | ``$($lens.schema)`` |")
}
[void]$sb.AppendLine('')
[void]$sb.AppendLine('## 2) Fusion stub (feeds shadow gate)')
[void]$sb.AppendLine('')
[void]$sb.AppendLine("| Key | Value |")
[void]$sb.AppendLine("| --- | --- |")
[void]$sb.AppendLine("| path | ``docs/final/artifacts/independent_lens_fusion_stub_latest.json`` |")
[void]$sb.AppendLine("| file_mtime_utc | ``$(Get-FileMtimeUtc $pFusion)`` |")
if ($fusionDoc) {
    [void]$sb.AppendLine("| version | ``$($fusionDoc.version)`` |")
    [void]$sb.AppendLine("| mode | ``$($fusionDoc.mode)`` |")
    $cs = $fusionDoc.consensus.consensus_sign
    if ($cs) { [void]$sb.AppendLine("| consensus.consensus_sign | ``$cs`` |") }
}
[void]$sb.AppendLine('')
[void]$sb.AppendLine('## 3) Shadow gate (weekly KPI SSOT)')
[void]$sb.AppendLine('')
[void]$sb.AppendLine("| Key | Value |")
[void]$sb.AppendLine("| --- | --- |")
[void]$sb.AppendLine("| path | ``docs/final/artifacts/independent_lens_shadow_gate_latest.json`` |")
[void]$sb.AppendLine("| file_mtime_utc | ``$(Get-FileMtimeUtc $pGate)`` |")
if ($gate) {
    [void]$sb.AppendLine("| decision | ``$($gate.decision)`` |")
    [void]$sb.AppendLine("| ts_utc | ``$($gate.ts_utc)`` |")
    $wc = $gate.history.weekly_cycles_observed
    $mc = $gate.history.monthly_cycles_observed
    if ($null -ne $wc) { [void]$sb.AppendLine("| history.weekly_cycles_observed | ``$wc`` |") }
    if ($null -ne $mc) { [void]$sb.AppendLine("| history.monthly_cycles_observed | ``$mc`` |") }
    $bl = $gate.blockers
    if ($bl) {
        $bj = ($bl | ConvertTo-Json -Compress -Depth 5)
        [void]$sb.AppendLine("| blockers (json) | ``$bj`` |")
    }
}
[void]$sb.AppendLine('')
[void]$sb.AppendLine('## 4) Role router S1 shadow advisory (tail)')
[void]$sb.AppendLine('')
[void]$sb.AppendLine("| Key | Value |")
[void]$sb.AppendLine("| --- | --- |")
[void]$sb.AppendLine("| path | ``reports/role_router_s1_shadow_advisory_log.jsonl`` |")
[void]$sb.AppendLine("| file_mtime_utc | ``$(Get-FileMtimeUtc $pAdvisoryLog)`` |")
if ($advisoryLine) {
    $escaped = $advisoryLine.Replace('`', '``').Replace('|', '\|')
    [void]$sb.AppendLine("| last_line | ``$escaped`` |")
}
else {
    [void]$sb.AppendLine('| last_line | *(empty or skipped)* |')
}

$parent = Split-Path -Parent $outMd
if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
[System.IO.File]::WriteAllText($outMd, $sb.ToString(), [System.Text.UTF8Encoding]::new($false))
Write-Host "WROTE: $outMd" -ForegroundColor Green
