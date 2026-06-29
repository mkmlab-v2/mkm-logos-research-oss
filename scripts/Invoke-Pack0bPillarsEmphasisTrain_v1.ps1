#Requires -Version 5.1
<#
.SYNOPSIS
  Pack 0-B pillars-only + birth-emphasis LoRA retrain (100 steps) + pillars curriculum eval.

.DESCRIPTION
  B-track [HYPO] research_only — no Track A / live promotion.
  Uses .venv_lora_local128 (cu128). Intended for Start-Process so runs survive terminal teardown.
  SSOT: reports/myeongri_pack0b_pillars_emphasis_experiment_spec_v1_latest.json
#>
param(
    [switch]$TrainOnly,
    [switch]$SkipTrain,
    [switch]$SkipLocked25,
    [switch]$Resume
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

$py = Join-Path $root ".venv_lora_local128\Scripts\python.exe"
$train = Join-Path $root "scripts\train_mkm_prophecy_lora_windows_fallback_v1.py"
$eval = Join-Path $root "scripts\run_myeongri_deterministic_lora_inference_eval_v1.py"
$prepSft = Join-Path $root "scripts\build_myeongri_pillars_only_sft_v1.py"
$log = Join-Path $root "reports\pack0b_pillars_emphasis_train_v1.log"
$watchJson = Join-Path $root "reports\pack0b_pillars_emphasis_watch_latest.json"
$lock = Join-Path $root "reports\pack0b_pillars_emphasis_train_v1.lock"

$sft = "data/training/myeongri_pillars_only_sft_birth_emphasis_v1.jsonl"
$goldenTrain = "data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl"
$locked = "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
$adapterOut = "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_pillars_emphasis_v1"
$evalReport25 = "reports/myeongri_pack0b_pillars_emphasis_locked25_eval.json"
$evalReport100 = "reports/myeongri_pack0b_pillars_emphasis_locked_eval_latest.json"
$pred25 = "reports/myeongri_pack0b_pillars_emphasis_locked25_predictions_latest.jsonl"
$pred100 = "reports/myeongri_pack0b_pillars_emphasis_locked_eval_predictions_latest.jsonl"

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
        & $py -u @PyArgs 2>&1 | ForEach-Object {
            $line = "$_"
            Add-Content -Path $log -Value $line -Encoding utf8
            Write-Host $line
        }
        return [int]$LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $prevEap
        if ($null -eq $prevUnbuf) { Remove-Item Env:PYTHONUNBUFFERED -ErrorAction SilentlyContinue }
        else { $env:PYTHONUNBUFFERED = $prevUnbuf }
    }
}

function Write-Watch([string]$Phase, [int]$LastStep, [bool]$TrainAlive, [string]$EvalReport = "") {
    $gpu = @{ memory_used_mib = $null; memory_total_mib = $null; utilization_pct = $null }
    try {
        $nv = & nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits 2>$null
        if ($nv) {
            $p = ($nv -split ',').ForEach({ $_.Trim() })
            if ($p.Count -ge 3) {
                $gpu = @{
                    memory_used_mib  = [int]$p[0]
                    memory_total_mib = [int]$p[1]
                    utilization_pct = [int]$p[2]
                }
            }
        }
    }
    catch { }

    $doc = @{
        schema       = "pack0b_pillars_emphasis_watch_v1"
        updated_utc  = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        phase        = $Phase
        train_alive  = $TrainAlive
        last_step    = $LastStep
        max_steps    = 100
        adapter_dir  = $adapterOut
        ordered_log  = "reports/pack0b_pillars_emphasis_train_v1.log"
        sft_jsonl    = $sft
        curriculum   = "pillars_only_v1"
        eval_report  = $EvalReport
        gpu          = $gpu
        track_wall   = @{ a_track_auto_promotion = $false; research_only = $true }
    } | ConvertTo-Json -Depth 6
    Set-Content -Path $watchJson -Value $doc -Encoding utf8
}

function Get-LastCheckpointStep([string]$OutDir) {
    $best = 0
    $dir = Join-Path $root $OutDir
    if (-not (Test-Path -LiteralPath $dir)) { return 0 }
    Get-ChildItem -Path $dir -Directory -Filter "checkpoint-*" -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.Name -match 'checkpoint-(\d+)$') {
            $s = [int]$Matches[1]
            if ($s -gt $best) { $best = $s }
        }
    }
    return $best
}

if (Test-Path -LiteralPath $lock) {
    $lockPid = (Get-Content -LiteralPath $lock -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($lockPid -and (Get-Process -Id $lockPid -ErrorAction SilentlyContinue)) {
        Write-Log "SKIP already running pillars_emphasis pid=$lockPid"
        exit 0
    }
    Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue
}
Set-Content -Path $lock -Value $PID -Encoding ascii

try {
    Write-Log "=== Pack0-B pillars_emphasis START train_only=$TrainOnly skip_train=$SkipTrain resume=$Resume pid=$PID ==="

    Write-Log "PHASE prep_sft"
    $rc = Invoke-PyLog -PyArgs @(
        $prepSft,
        "--input-jsonl", $goldenTrain,
        "--output-jsonl", $sft
    )
    if ($rc -ne 0) { throw "prep_sft failed exit=$rc" }

    if (-not $SkipTrain) {
        Write-Watch -Phase "training" -LastStep (Get-LastCheckpointStep $adapterOut) -TrainAlive $true
        Write-Log "PHASE train100 curriculum=pillars_only_v1 out=$adapterOut"
        $trainArgs = @(
            $train,
            "--dataset-path", $sft,
            "--model-name", "Qwen/Qwen2.5-7B-Instruct",
            "--max-seq-length", "4096",
            "--max-steps", "100",
            "--save-steps", "20",
            "--batch-size", "1",
            "--grad-accum", "8",
            "--learning-rate", "0.0001",
            "--lora-r", "16",
            "--lora-alpha", "32",
            "--lora-dropout", "0.05",
            "--output-dir", $adapterOut
        )
        if ($Resume) { $trainArgs += "--resume" }
        $rc = Invoke-PyLog -PyArgs $trainArgs
        if ($rc -ne 0) { throw "train failed exit=$rc" }
    }

    Write-Watch -Phase "idle" -LastStep (Get-LastCheckpointStep $adapterOut) -TrainAlive $false

    if ($TrainOnly) {
        Write-Log "=== DONE train_only exit=0 ==="
        exit 0
    }

    function Invoke-PillarsEval([string]$Label, [string]$ReportJson, [string]$PredJsonl, [int]$Limit) {
        Write-Log "PHASE eval_$Label pillars_only adapter=$adapterOut limit=$Limit"
        $evalArgs = @(
            $eval,
            "--golden-jsonl", $locked,
            "--adapter-path", $adapterOut,
            "--profile-key", "train_default",
            "--pillars-only-curriculum",
            "--predictions-jsonl", $PredJsonl,
            "--report-json", $ReportJson,
            "--split", "locked_eval"
        )
        if ($Limit -gt 0) { $evalArgs += @("--limit", "$Limit") }
        $rc = Invoke-PyLog -PyArgs $evalArgs
        if ($rc -ne 0) { throw "eval $Label failed exit=$rc" }
        return $ReportJson
    }

    $align25 = 0.0
    if (-not $SkipLocked25) {
        $null = Invoke-PillarsEval -Label "locked25" -ReportJson $evalReport25 -PredJsonl $pred25 -Limit 25
    }
    if (Test-Path -LiteralPath (Join-Path $root $evalReport25)) {
        try {
            $ev = Get-Content -LiteralPath (Join-Path $root $evalReport25) -Raw -Encoding utf8 | ConvertFrom-Json
            $align25 = [double]($ev.alignment_pass_rate)
        }
        catch {
            Write-Log "WARN locked25 report parse failed: $_"
        }
        Write-Log "locked25 pillars_alignment_pass_rate=$align25"
    }

    $r100 = Invoke-PillarsEval -Label "locked100" -ReportJson $evalReport100 -PredJsonl $pred100 -Limit 0
    Write-Watch -Phase "eval_done" -LastStep 100 -TrainAlive $false -EvalReport $evalReport100

    Write-Log "PHASE refresh_triage"
    $rc = Invoke-PyLog -PyArgs @( (Join-Path $root "scripts\build_myeongri_pack0b_adapter_locked_triage_v1.py") )
    if ($rc -ne 0) { Write-Log "WARN triage refresh exit=$rc" }

    Write-Log "=== DONE pillars_emphasis pipeline exit=0 locked25_align=$align25 ==="
}
finally {
    if (Test-Path -LiteralPath $lock) { Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue }
}
exit 0
