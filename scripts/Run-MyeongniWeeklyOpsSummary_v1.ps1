<#
.SYNOPSIS
  Weekly minimal Myeongni ops loop: independent lens -> fusion stub -> shadow gate -> thin MD summary.

.DESCRIPTION
  Step 2 KPI is locked to independent_lens_shadow_gate_latest.json (CONSTITUTION / ops agreement).
  Shadow gate requires independent_lens_fusion_stub_latest.json; this script refreshes the stub first.

  Optional: -Include16StateProbe runs myeongni_summary_gen.py on the default experiment JSONL to refresh
  data/myeongni/16_STATE_MASTER_PROBE_v1.json (coverage_summary.states_with_audit).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-MyeongniWeeklyOpsSummary_v1.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-MyeongniWeeklyOpsSummary_v1.ps1 -Include16StateProbe
#>
[CmdletBinding()]
param(
    [switch]$Include16StateProbe,
    [switch]$SkipLens,
    [switch]$SkipFusionAndGate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$lens = Join-Path $PSScriptRoot "run_lens_myeongni.py"
$fusionStub = Join-Path $PSScriptRoot "report_independent_lens_fusion_stub_v0.py"
$shadowGate = Join-Path $PSScriptRoot "report_independent_lens_shadow_gate.py"
$probeGen = Join-Path $PSScriptRoot "myeongni_summary_gen.py"
$emitMd = Join-Path $PSScriptRoot "emit_myeongni_weekly_ops_summary_v1.py"

foreach ($p in @($lens, $fusionStub, $shadowGate, $emitMd)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Required script not found: $p"
    }
}
if ($Include16StateProbe -and -not (Test-Path -LiteralPath $probeGen)) {
    throw "Required script not found: $probeGen"
}

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "[myeongni-weekly] $Name"
    Set-Location -LiteralPath $repoRoot
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit=$LASTEXITCODE)"
    }
}

if (-not $SkipLens) {
    Invoke-Step -Name "run_lens_myeongni.py (--allow-fallback)" -Action {
        py $lens --allow-fallback
    }
}

if (-not $SkipFusionAndGate) {
    Invoke-Step -Name "report_independent_lens_fusion_stub_v0.py" -Action {
        py $fusionStub
    }
    Invoke-Step -Name "report_independent_lens_shadow_gate.py (KPI lock-on)" -Action {
        py $shadowGate
    }
}

$probePath = Join-Path $repoRoot "data\myeongni\16_STATE_MASTER_PROBE_v1.json"
$auditJsonl = Join-Path $repoRoot "data\myeongni\myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"

if ($Include16StateProbe) {
    if (-not (Test-Path -LiteralPath $auditJsonl)) {
        throw "16-state probe audit JSONL not found: $auditJsonl"
    }
    Invoke-Step -Name "myeongni_summary_gen.py (MASTER_PROBE)" -Action {
        py $probeGen --audit-path $auditJsonl --output $probePath
    }
}

$emitArgs = @($emitMd, "--out", (Join-Path $repoRoot "reports\myeongni_weekly_ops_summary_latest.md"))
if ($Include16StateProbe) {
    $emitArgs += @("--probe-json", $probePath)
}

Invoke-Step -Name "emit_myeongni_weekly_ops_summary_v1.py" -Action {
    py @emitArgs
}

Write-Host "[myeongni-weekly] PASS"
Write-Host "[myeongni-weekly] summary_md=$repoRoot\reports\myeongni_weekly_ops_summary_latest.md"
Write-Host "[myeongni-weekly] gate_json=$repoRoot\docs\final\artifacts\independent_lens_shadow_gate_latest.json"
