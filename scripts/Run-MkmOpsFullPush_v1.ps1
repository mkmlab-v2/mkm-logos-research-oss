# MKM ops one-click: P0 -> Git -> Fact-Lock -> prophecy closure -> showroom VPS (+ optional nginx reload) -> pytest pack -> Pack0-B convert+fit -> premium queue drain -> jemaai probe (browser UA) -> athena_checkpoint.
# No live trading. VPS step needs SSH/scp configured like sync_showroom_to_vps.ps1.
#
# Usage (repo root or any cwd):
#   pwsh -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\Run-MkmOpsFullPush_v1.ps1
#   pwsh ... -File ...\Run-MkmOpsFullPush_v1.ps1 -SkipFactLock -SkipVpsSync   # fast smoke
#
param(
    [string]$WorkspaceRoot = "",
    [switch]$SkipP0,
    [switch]$SkipGit,
    [switch]$SkipFactLock,
    [switch]$SkipProphecyClosure,
    [switch]$SkipVpsSync,
    [switch]$SkipVpsNginxReload,
    [switch]$SkipPytestPack,
    [switch]$SkipPack0b,
    [switch]$SkipPremiumDrain,
    [switch]$SkipJemaaiProbe,
    [switch]$SkipCheckpoint
)

$ErrorActionPreference = "Stop"
if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}
else {
    $root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
}
Set-Location -LiteralPath $root

$maint = [System.Environment]::GetEnvironmentVariable("MKM_WORKSPACE_MAINTENANCE")
if ($maint -and ($maint.Trim().ToLower() -in @("1", "true", "yes", "on"))) {
    Write-Host "SKIP: MKM_WORKSPACE_MAINTENANCE active" -ForegroundColor Yellow
    exit 0
}

function Invoke-Step {
    param([string]$Title, [scriptblock]$Action)
    Write-Host "=== $Title ===" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed ($Title) exit=$LASTEXITCODE"
    }
}

if (-not $SkipP0) {
    Invoke-Step "P0 constitution paths" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\verify_p0_constitution_gate_paths.ps1")
    }
}

if (-not $SkipGit) {
    Invoke-Step "Git workspace sanity" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Verify-GitWorkspaceSanity.ps1")
    }
}

if (-not $SkipFactLock) {
    Invoke-Step "Fact-Lock bundle" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\run_fact_lock_bundle.ps1") -SafeOpsIgnoreLiveSync
    }
}

if (-not $SkipProphecyClosure) {
    Invoke-Step "Prophecy lane closure bundle" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1") `
            -SkipLiveSyncPull -SkipGoNoGoRefresh -SkipWebhook
    }
}

if (-not $SkipVpsSync) {
    if (-not $SkipVpsNginxReload) {
        $env:JEMAAI_VPS_RELOAD_NGINX = "1"
    }
    Invoke-Step "Showroom -> VPS (+ nginx if JEMAAI_VPS_RELOAD_NGINX)" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\sync_showroom_to_vps.ps1") -RefreshStaging -SkipDotenvUserSync
    }
}

if (-not $SkipPytestPack) {
    Invoke-Step "Pytest ops pack (4)" {
        $tests = @(
            (Join-Path $root "tests\test_validate_showroom_public_bundle.py"),
            (Join-Path $root "tests\test_mkm_control_integrity_pipeline_smoke_v1.py"),
            (Join-Path $root "tests\test_run_pack0b_deterministic_lora_pipeline_v1.py"),
            (Join-Path $root "tests\test_myeongri_deterministic_lora_pack_copy_guardrails_v1.py")
        )
        & py -m pytest @($tests + @("-q", "--tb=short"))
    }
}

if (-not $SkipPack0b) {
    $sft = Join-Path $root "reports\_pack0b_auto_push_sft.jsonl"
    $fit = Join-Path $root "reports\_pack0b_auto_push_fit.json"
    $golden = Join-Path $root "tests\fixtures\myeongri_deterministic_lora_golden_sample_v1.jsonl"
    Invoke-Step "Pack0-B convert + golden fit (no train)" {
        & py (Join-Path $root "scripts\run_pack0b_deterministic_lora_pipeline_v1.py") `
            --golden-jsonl $golden --sft-jsonl $sft --fit-report-out $fit
    }
}

if (-not $SkipPremiumDrain) {
    Invoke-Step "Premium multilens queue drain" {
        & py (Join-Path $root "scripts\premium_multilens_job_queue_stub_v1.py") drain --allow-missing-queue --write-ack
    }
}

if (-not $SkipJemaaiProbe) {
    Invoke-Step "jemaai.cloud poll (browser UA)" {
        $py = @"
import urllib.request
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
req = urllib.request.Request('https://jemaai.cloud/public_showroom_poll.html', headers={'User-Agent': UA})
with urllib.request.urlopen(req, timeout=30) as r:
    print('GET', r.status)
"@
        & py -c $py
    }
}

if (-not $SkipCheckpoint) {
    $stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $oneLine = "Run-MkmOpsFullPush_v1 OK $stamp"
    Invoke-Step "athena_checkpoint" {
        & py (Join-Path $root "scripts\athena_checkpoint.py") $oneLine
    }
}

Write-Host "=== Run-MkmOpsFullPush_v1: all requested steps OK ===" -ForegroundColor Green
exit 0
