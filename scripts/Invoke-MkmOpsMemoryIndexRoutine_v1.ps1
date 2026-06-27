<#
.SYNOPSIS
  Ops memory index routine — build, gate, resume pack, optional token bench.

.DESCRIPTION
  [HYPO] / research_only / B-track. No Track A·live trading auto-merge.

  1) build_mkm_ops_memory_index_v1.py (+ source must_keep gate)
  2) build_mkm_chat_resume_pack_v1.py (+ inject must_keep gate)
  3) bench_mkm_ops_memory_index_token_savings_v1.py (optional)

.PARAMETER SkipBench
  Skip tiktoken/char token bench.

.PARAMETER DryRunIndex
  Pass --dry-run to index builder only.

.PARAMETER IncludeSlice
  [HYPO] Phase 0.5 — pass --include-slice to resume pack builder.

.PARAMETER RepairV2Slice
  [HYPO] repair_v2 noise-guard slices (overrides IncludeSlice).

.PARAMETER SliceMaxChars
  Max chars per anchor slice preview (default 1200).
.PARAMETER IncludeA2aPilot
  [HYPO] tp01 — run build_mkm_chat_resume_a2a_pilot_v1.py after token bench (B-track wire only).
.PARAMETER Lane
  oracle | ms | infra | web_ops — pass to resume pack builder.

.PARAMETER ResumeMode
  Standard (default) or AdvancedLogos — 「장기기억 맥락이어 고급해석」 (forces oracle lane when AdvancedLogos).
#>
param(
    [switch]$SkipBench,
    [switch]$DryRunIndex,
    [switch]$IncludeSlice,
    [switch]$RepairV2Slice,
    [switch]$IncludeA2aPilot,
    [int]$SliceMaxChars = 1200,
    [ValidateSet("oracle", "ms", "infra", "web_ops", "design")]
    [string]$Lane = "",
    [ValidateSet("", "Standard", "AdvancedLogos")]
    [string]$ResumeMode = ""
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
Set-Location -LiteralPath $root

if ($ResumeMode -eq "AdvancedLogos" -and -not $Lane) {
    $Lane = "oracle"
}
$resumeModePy = if ($ResumeMode -eq "AdvancedLogos") { "advanced_logos" } else { "standard" }

function Invoke-Step {
    param([string]$Name, [string[]]$Command)
    Write-Host "==> $Name"
    Write-Host ($Command -join " ")
    & $Command[0] $Command[1..($Command.Length - 1)]
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit $LASTEXITCODE"
    }
}

Invoke-Step -Name "build_constitution_sidecar" -Command @(
    "py", "scripts/build_mkm_sidecar_constitution_paths_v1.py", "--skip-if-unchanged"
)

$indexArgs = @("py", "scripts/build_mkm_ops_memory_index_v1.py")
if ($DryRunIndex) { $indexArgs += "--dry-run" }
Invoke-Step -Name "build_ops_memory_index" -Command $indexArgs

if (-not $DryRunIndex) {
    Invoke-Step -Name "must_keep_gate_source" -Command @(
        "py", "scripts/check_mkm_ops_memory_must_keep_gate_v1.py", "--phase", "source"
    )
    if ($Lane -eq "oracle") {
        Invoke-Step -Name "merge_logos_math_overlay_oracle" -Command @(
            "py", "scripts/build_mkm_ops_memory_logos_math_overlay_v1.py"
        )
    }
    if ($Lane -eq "design") {
        Invoke-Step -Name "merge_domain_adapters_overlay_design" -Command @(
            "py", "scripts/build_mkm_ops_memory_domain_adapters_overlay_v1.py"
        )
    }
    $resumeArgs = @("py", "scripts/build_mkm_chat_resume_pack_v1.py", "--resume-mode", $resumeModePy)
    if ($Lane) {
        $resumeArgs += @("--lane", $Lane, "--infer-topic-from-lane")
    }
    if ($RepairV2Slice) {
        $resumeArgs += @("--repair-v2-slice", "--slice-max-chars", "$SliceMaxChars")
    } elseif ($IncludeSlice) {
        $resumeArgs += @("--include-slice", "--slice-max-chars", "$SliceMaxChars")
    }
    Invoke-Step -Name "build_chat_resume_pack" -Command $resumeArgs
    if (-not $SkipBench) {
        Invoke-Step -Name "token_bench_hypo" -Command @(
            "py", "scripts/bench_mkm_ops_memory_index_token_savings_v1.py"
        )
    }
    if ($IncludeA2aPilot) {
        $pilotArgs = @("py", "scripts/build_mkm_chat_resume_a2a_pilot_v1.py")
        if ($IncludeSlice) {
            $pilotArgs += @("--include-slice", "--slice-max-chars", "$SliceMaxChars")
        }
        if ($Lane) {
            $pilotArgs += @("--lane", $Lane)
        }
        Invoke-Step -Name "a2a_tp01_resume_pilot_hypo" -Command $pilotArgs
    }
}

Write-Host "OK: Invoke-MkmOpsMemoryIndexRoutine_v1 completed"
