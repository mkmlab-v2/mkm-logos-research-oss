# [HYPO] Prism staging bundle + n40 dogfood + coding proxy auto chain (research_only).
param(
    [switch]$SkipPrismBundle,
    [switch]$SkipPrismWireBench,
    [switch]$SkipProxyChain,
    [switch]$SkipDogfood,
    [switch]$SkipN40Extract,
    [int]$DogfoodMaxCases = 10
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$N40 = "data/btrack/cursor_coding_compress_bench_v1_n40.jsonl"
$Results = "experiments/no_guard_limit_test/results"

function Invoke-Step {
    param([string]$Label, [scriptblock]$Block)
    Write-Host "[$Label]" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Label (exit=$LASTEXITCODE)" }
}

if (-not $SkipPrismBundle) {
    $bundleArgs = @("scripts/sandbox/run_prism_meta_channel_staging_bundle_v1.py", "--run-pytest", "--require-staging-enable")
    if ($SkipPrismWireBench) { $bundleArgs += "--skip-wire-bench" }
    Invoke-Step "prism staging bundle" { py @bundleArgs }

    Invoke-Step "n40 dogfood extension" {
        py scripts/sandbox/build_prism_n40_dogfood_report_v1.py --strict
    }
}

if (-not $SkipProxyChain) {
    Invoke-Step "coding proxy auto chain" {
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-CursorCodingProxyAutoChain_v1.ps1
    }
}

if (-not $SkipDogfood) {
    $prev = $env:MKM_PRISM_META_CHANNEL_BTRACK
    try {
        $env:MKM_PRISM_META_CHANNEL_BTRACK = "1"
        Invoke-Step "staging live smoke (env=ON, n40)" {
            py scripts/sandbox/run_prism_meta_channel_staging_live_smoke_v1.py `
                --input-jsonl $N40 `
                --max-cases $DogfoodMaxCases `
                --strict
        }
    }
    finally {
        if ($null -eq $prev) {
            Remove-Item Env:MKM_PRISM_META_CHANNEL_BTRACK -ErrorAction SilentlyContinue
        }
        else {
            $env:MKM_PRISM_META_CHANNEL_BTRACK = $prev
        }
    }
}

if (-not $SkipN40Extract) {
    Invoke-Step "agent-extract gate (n40)" {
        py scripts/run_cursor_coding_agent_extract_gate_v1.py --input-jsonl $N40
    }
}

Write-Host "Prism+proxy unified chain OK" -ForegroundColor Green
