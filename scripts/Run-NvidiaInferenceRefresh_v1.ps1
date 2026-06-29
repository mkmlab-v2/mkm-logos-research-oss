#Requires -Version 5.1
<#
.SYNOPSIS
  Refresh B-track inference stack: NIM smoke, API primary, hybrid A/B, Logos, v28 adapter, brief.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-NvidiaInferenceRefresh_v1.ps1
#>
param(
    [switch]$SkipAb,
    [switch]$SkipV28Infer,
    [switch]$SkipLargeNim
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$fail = 0

function Step($name, [scriptblock] $block) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    & $block
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] $name exit=$LASTEXITCODE" -ForegroundColor Red
        $script:fail = 1
    }
    else {
        Write-Host "[OK] $name" -ForegroundColor Green
    }
}

Step 'nim_smoke' { py scripts/nvidia_nim_chat_v1.py smoke }
Step 'api_primary' { py scripts/run_nvidia_api_primary_lane_v1.py }
if (-not $SkipLargeNim) {
    Step 'nim_large_smoke' { py scripts/nvidia_nim_large_model_smoke_v1.py }
}
Step 'hybrid_chain' { py scripts/run_hybrid_local_nim_chain_v1.py }
if (-not $SkipAb) {
    Step 'hybrid_ab' { py scripts/run_hybrid_local_vs_nim_ab_v1.py }
}
Step 'logos_handoff' { py scripts/run_nim_logos_research_handoff_v1.py }
if (-not $SkipV28Infer) {
    Step 'v28_infer_auto' { py scripts/run_nemotron_v28_adapter_inference_smoke_v1.py --mode auto }
}
Step 'parallel_brief' { py scripts/build_nemotron_parallel_research_brief_v1.py }
Step 'hybrid_lab_status' { py scripts/build_hybrid_ai_lab_status_v1.py }

Write-Host "`n=== inference refresh fail=$fail ===" -ForegroundColor $(if ($fail) { 'Red' } else { 'Green' })
exit $fail
