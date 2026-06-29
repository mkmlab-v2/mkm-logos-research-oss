#Requires -Version 5.1
<#
.SYNOPSIS
  Pack 0-B ordered GPU train: smoke100 -> locked_eval -> full500 -> locked_eval.

.DESCRIPTION
  Uses .venv_lora_local128 (cu128). Intended for Start-Process / Task Scheduler
  so long runs survive Cursor terminal teardown.
#>
param(
    [switch]$SmokeOnly,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

$py = Join-Path $root ".venv_lora_local128\Scripts\python.exe"
$train = Join-Path $root "scripts\train_mkm_prophecy_lora_windows_fallback_v1.py"
$eval = Join-Path $root "scripts\run_myeongri_deterministic_lora_inference_eval_v1.py"
$log = Join-Path $root "reports\pack0b_ordered_train_v1.log"
$sft = "data/training/myeongri_deterministic_lora_sft_train_v1.jsonl"
$locked = "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
$smokeOut = "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_smoke100_v1"
# Qwen full500 — do NOT reuse run_pack0b_pipeline_latest (legacy TinyLlama checkpoints).
$fullOut = "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_full500_v1"

if (-not (Test-Path -LiteralPath $py)) {
    Write-Error "Missing $py — run cu128 venv bootstrap first."
}

function Write-Log([string]$msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')] $msg"
    Add-Content -Path $log -Value $line -Encoding utf8
    Write-Host $line
}

function Invoke-PyLog([string[]]$PyArgs) {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $prevUnbuf = $env:PYTHONUNBUFFERED
    $env:PYTHONUNBUFFERED = "1"
    try {
        $output = & $py -u @PyArgs 2>&1 | ForEach-Object {
            $line = "$_"
            Add-Content -Path $log -Value $line -Encoding utf8
            $line
        }
        return [int]$LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $prevEap
        if ($null -eq $prevUnbuf) { Remove-Item Env:PYTHONUNBUFFERED -ErrorAction SilentlyContinue }
        else { $env:PYTHONUNBUFFERED = $prevUnbuf }
    }
}

function Invoke-Train(
    [string]$Label,
    [string]$OutDir,
    [int]$MaxSteps,
    [int]$SaveSteps,
    [switch]$Resume
) {
    Write-Log "PHASE $Label train max_steps=$MaxSteps save_steps=$SaveSteps out=$OutDir"
    $trainArgs = @(
        $train,
        "--dataset-path", $sft,
        "--model-name", "Qwen/Qwen2.5-7B-Instruct",
        "--max-seq-length", "4096",
        "--max-steps", "$MaxSteps",
        "--save-steps", "$SaveSteps",
        "--batch-size", "1",
        "--grad-accum", "8",
        "--learning-rate", "0.0001",
        "--lora-r", "16",
        "--lora-alpha", "32",
        "--lora-dropout", "0.05",
        "--output-dir", $OutDir
    )
    if ($Resume) { $trainArgs += "--resume" }
    $rc = Invoke-PyLog -PyArgs $trainArgs
    if ($rc -ne 0) { throw "train failed ($Label) exit=$rc" }
}

function Invoke-Eval([string]$Label, [string]$AdapterDir, [string]$ReportJson) {
    Write-Log "PHASE $Label locked_eval eval adapter=$AdapterDir"
    $evalArgs = @(
        $eval,
        "--golden-jsonl", $locked,
        "--adapter-path", $AdapterDir,
        "--profile-key", "train_default",
        "--predictions-jsonl", "reports/myeongri_deterministic_lora_locked_eval_predictions_${Label}_latest.jsonl",
        "--report-json", $ReportJson,
        "--split", "locked_eval"
    )
    $rc = Invoke-PyLog -PyArgs $evalArgs
    if ($rc -ne 0) { throw "eval failed ($Label) exit=$rc" }
}

$lock = Join-Path $root "reports\pack0b_ordered_train_v1.lock"
if (Test-Path -LiteralPath $lock) {
    $lockPid = (Get-Content -LiteralPath $lock -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($lockPid -and (Get-Process -Id $lockPid -ErrorAction SilentlyContinue)) {
        Write-Log "SKIP already running pipeline pid=$lockPid (lock=$lock)"
        exit 0
    }
    Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue
}
Set-Content -Path $lock -Value $PID -Encoding ascii

try {
Write-Log "=== Pack0-B ordered train START smoke_only=$SmokeOnly skip_smoke=$SkipSmoke pid=$PID ==="

Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*train_mkm_prophecy_lora_windows_fallback_v1.py*'
} | ForEach-Object {
    $isVenv = $_.CommandLine -like '*\.venv_lora_local128\*'
    Write-Log "stale train pid=$($_.ProcessId) venv=$isVenv — stopping"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

$smokeEvalReport = "reports/myeongri_deterministic_lora_locked_eval_inference_eval_smoke100_latest.json"

if (-not $SkipSmoke) {
    $smokeCkpt100 = Join-Path $smokeOut "checkpoint-100"
    $smokeEvalDone = Test-Path -LiteralPath $smokeEvalReport
    if ($smokeEvalDone) {
        Write-Log "SKIP smoke100 — eval report present ($smokeEvalReport)"
    }
    else {
        if (Test-Path -LiteralPath $smokeCkpt100) {
            Write-Log "SKIP smoke100 train — checkpoint-100 present; eval only"
        }
        else {
            $smokeResume = @(Get-ChildItem -Path $smokeOut -Directory -Filter "checkpoint-*" -ErrorAction SilentlyContinue).Count -gt 0
            Invoke-Train -Label "smoke100" -OutDir $smokeOut -MaxSteps 100 -SaveSteps 10 -Resume:($smokeResume)
        }
        Invoke-Eval -Label "smoke100" -AdapterDir $smokeOut -ReportJson $smokeEvalReport
    }
}
else {
    Write-Log "SKIP smoke100 (SkipSmoke)"
}

if ($SmokeOnly) {
    Write-Log "=== DONE smoke_only exit=0 ==="
    exit 0
}

$fullResume = @(Get-ChildItem -Path $fullOut -Directory -Filter "checkpoint-*" -ErrorAction SilentlyContinue).Count -gt 0
Invoke-Train -Label "full500" -OutDir $fullOut -MaxSteps 500 -SaveSteps 50 -Resume:($fullResume)
Invoke-Eval -Label "full500" -AdapterDir $fullOut -ReportJson "reports/myeongri_deterministic_lora_locked_eval_inference_eval_latest.json"

Write-Log "PHASE post_eval sovereignty SSOT refresh (pack0b rail isolated from market verdict)"
py scripts/build_lens_sovereignty_supplementary_rails_v1_2.py
if ($LASTEXITCODE -ne 0) { Write-Log "WARN supplementary rails exit=$LASTEXITCODE" }
py scripts/build_p0_role_contract_experiment_results_v1.py
if ($LASTEXITCODE -ne 0) { Write-Log "WARN p0 results exit=$LASTEXITCODE" }
py scripts/build_lens_sovereignty_report_v1.py --blueprint docs/final/artifacts/lens_sovereignty_blueprint_v1_2.json
if ($LASTEXITCODE -ne 0) { Write-Log "WARN sovereignty report exit=$LASTEXITCODE" }
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-Pack0bFull500WatchStatus_v1.ps1 -Once | ForEach-Object { Write-Log $_ }

Write-Log "=== DONE ordered pipeline exit=0 ==="
}
finally {
    if (Test-Path -LiteralPath $lock) { Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue }
}
exit 0
