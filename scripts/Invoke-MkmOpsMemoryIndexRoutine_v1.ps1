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
#>
param(
    [switch]$SkipBench,
    [switch]$DryRunIndex
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
Set-Location -LiteralPath $root

function Invoke-Step {
    param([string]$Name, [string[]]$Command)
    Write-Host "==> $Name"
    Write-Host ($Command -join " ")
    & $Command[0] $Command[1..($Command.Length - 1)]
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit $LASTEXITCODE"
    }
}

$indexArgs = @("py", "scripts/build_mkm_ops_memory_index_v1.py")
if ($DryRunIndex) { $indexArgs += "--dry-run" }
Invoke-Step -Name "build_ops_memory_index" -Command $indexArgs

if (-not $DryRunIndex) {
    Invoke-Step -Name "must_keep_gate_source" -Command @(
        "py", "scripts/check_mkm_ops_memory_must_keep_gate_v1.py", "--phase", "source"
    )
    Invoke-Step -Name "build_chat_resume_pack" -Command @(
        "py", "scripts/build_mkm_chat_resume_pack_v1.py"
    )
    if (-not $SkipBench) {
        Invoke-Step -Name "token_bench_hypo" -Command @(
            "py", "scripts/bench_mkm_ops_memory_index_token_savings_v1.py"
        )
    }
}

Write-Host "OK: Invoke-MkmOpsMemoryIndexRoutine_v1 completed"
