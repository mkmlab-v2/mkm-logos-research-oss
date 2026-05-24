# Monitor external Qwen Pack0B train; on success run locked_eval pillars (limit 25).
# Usage: pwsh -NoProfile -File scripts/Watch-QwenPack0bTrainAndEval_v1.ps1
param(
    [int]$PollSeconds = 120,
    [int]$EvalLimit = 25,
    [string]$AdapterDir = "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_qwen_compact_v1"
)

$ErrorActionPreference = "Stop"
$Root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT } else { "C:\workspace" }
Set-Location $Root

$adapterPath = Join-Path $Root $AdapterDir
$adapterCfg = Join-Path $adapterPath "adapter_config.json"
$golden = Join-Path $Root "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
$errLog = Join-Path $Root "reports/qwen_pack0b_compact_train_external.err.log"
$watchLog = Join-Path $Root "reports/qwen_pack0b_compact_watch.log"
$statusJson = Join-Path $Root "reports/qwen_pack0b_compact_watch_latest.json"

function Write-Status($obj) {
    $obj | ConvertTo-Json -Depth 6 | Set-Content -Path $statusJson -Encoding utf8
}

function Get-TrainPid {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -match "train_mkm_prophecy_lora_windows" -and $_.CommandLine -match "run_pack0b_qwen_compact" } |
        Select-Object -ExpandProperty ProcessId -First 1
}

function Get-LastStep {
    if (-not (Test-Path $errLog)) { return $null }
    $m = Select-String -Path $errLog -Pattern "(\d+)/300" -AllMatches | Select-Object -Last 1
    if ($m -and $m.Matches.Count -gt 0) { return $m.Matches[-1].Groups[1].Value }
    return $null
}

"watch started $(Get-Date -Format o)" | Add-Content $watchLog

while ($true) {
    $step = Get-LastStep
    $trainPid = Get-TrainPid
    $alive = $false
    if ($trainPid) {
        $alive = $null -ne (Get-Process -Id $trainPid -ErrorAction SilentlyContinue)
    }

    Write-Status @{
        schema          = "qwen_pack0b_compact_watch_v1"
        updated_utc     = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        phase           = "training"
        train_pid       = $trainPid
        train_alive     = $alive
        last_step       = $step
        adapter_ready   = (Test-Path $adapterCfg)
        adapter_path    = $adapterPath
    }

    if (Test-Path $adapterCfg) {
        "adapter ready $(Get-Date -Format o)" | Add-Content $watchLog
        break
    }

    if ($trainPid -and -not $alive) {
        "train process exited without adapter $(Get-Date -Format o)" | Add-Content $watchLog
        if (-not (Test-Path $adapterCfg)) {
            Write-Status @{
                schema      = "qwen_pack0b_compact_watch_v1"
                updated_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
                phase       = "failed"
                error       = "train_exited_no_adapter"
                last_step   = $step
            }
            exit 2
        }
        break
    }

    if (-not $trainPid -and -not (Test-Path $adapterCfg)) {
        "no train pid and no adapter $(Get-Date -Format o)" | Add-Content $watchLog
        Write-Status @{
            schema      = "qwen_pack0b_compact_watch_v1"
            updated_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            phase       = "failed"
            error       = "no_train_process"
        }
        exit 3
    }

    Start-Sleep -Seconds $PollSeconds
}

Write-Status @{
    schema        = "qwen_pack0b_compact_watch_v1"
    updated_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    phase         = "eval"
    adapter_ready = $true
    eval_limit    = $EvalLimit
}

$evalLog = Join-Path $Root "reports/qwen_pack0b_compact_eval_external.log"
$evalErr = Join-Path $Root "reports/qwen_pack0b_compact_eval_external.err.log"

$evalArgs = @(
    "scripts/run_myeongri_deterministic_lora_inference_eval_v1.py",
    "--golden-jsonl", $golden,
    "--adapter-path", $adapterPath,
    "--profile-key", "train_default",
    "--split", "locked_eval",
    "--alignment-tier", "pillars",
    "--compact-instruction",
    "--limit", "$EvalLimit",
    "--predictions-jsonl", (Join-Path $Root "reports/myeongri_deterministic_lora_locked_eval_predictions_qwen_compact_v1.jsonl"),
    "--report-json", (Join-Path $Root "reports/myeongri_deterministic_lora_locked_eval_inference_eval_qwen_compact_v1.json")
)

"eval start $(Get-Date -Format o) $($evalArgs -join ' ')" | Add-Content $watchLog
$p = Start-Process -FilePath "py" -ArgumentList $evalArgs -WorkingDirectory $Root -PassThru -Wait -NoNewWindow -RedirectStandardOutput $evalLog -RedirectStandardError $evalErr
$rc = $p.ExitCode

Write-Status @{
    schema        = "qwen_pack0b_compact_watch_v1"
    updated_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    phase         = if ($rc -eq 0) { "done" } else { "eval_failed" }
    eval_exit     = $rc
    report_json   = "reports/myeongri_deterministic_lora_locked_eval_inference_eval_qwen_compact_v1.json"
    predictions   = "reports/myeongri_deterministic_lora_locked_eval_predictions_qwen_compact_v1.jsonl"
}

"eval exit $rc $(Get-Date -Format o)" | Add-Content $watchLog
exit $rc
