# Monitor external interpret LoRA train; on success run eval + Harness v2 smoke.
param(
    [int]$PollSeconds = 60,
    [int]$EvalLimit = 25,
    [int]$HarnessLimit = 5,
    [string]$AdapterDir = "storage/adapters/myeongri_interpret_lora_v0/run_qwen_interpret_v1"
)

$ErrorActionPreference = "Stop"
$Root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT } else { "C:\workspace" }
Set-Location $Root

$adapterPath = Join-Path $Root $AdapterDir
$adapterCfg = Join-Path $adapterPath "adapter_config.json"
$errLog = Join-Path $Root "reports/myeongri_interpret_qwen_train_external.err.log"
$watchLog = Join-Path $Root "reports/myeongri_interpret_watch.log"
$statusJson = Join-Path $Root "reports/myeongri_interpret_watch_latest.json"

function Write-Status($obj) {
    $obj | ConvertTo-Json -Depth 8 | Set-Content -Path $statusJson -Encoding utf8
}

function Get-TrainPid {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -match "train_mkm_prophecy_lora_windows" -and
            $_.CommandLine -match "myeongri_interpret_sft_v1"
        } |
        Select-Object -ExpandProperty ProcessId -First 1
}

function Get-LastStep {
    if (-not (Test-Path $errLog)) { return $null }
    $m = Select-String -Path $errLog -Pattern "(\d+)/300" -AllMatches | Select-Object -Last 1
    if ($m -and $m.Matches.Count -gt 0) { return $m.Matches[-1].Groups[1].Value }
    return $null
}

"interpret watch started $(Get-Date -Format o)" | Add-Content $watchLog

while ($true) {
    $step = Get-LastStep
    $trainPid = Get-TrainPid
    $alive = $false
    if ($trainPid) {
        $alive = $null -ne (Get-Process -Id $trainPid -ErrorAction SilentlyContinue)
    }

    Write-Status @{
        schema        = "myeongri_interpret_watch_v1"
        updated_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        phase         = "training"
        train_pid     = $trainPid
        train_alive   = $alive
        last_step     = $step
        adapter_ready = (Test-Path $adapterCfg)
        adapter_path  = $adapterPath
    }

    if (Test-Path $adapterCfg) {
        "adapter ready $(Get-Date -Format o)" | Add-Content $watchLog
        break
    }

    if ($trainPid -and -not $alive) {
        "train exited without adapter $(Get-Date -Format o)" | Add-Content $watchLog
        if (-not (Test-Path $adapterCfg)) {
            Write-Status @{
                schema      = "myeongri_interpret_watch_v1"
                updated_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
                phase       = "failed"
                error       = "train_exited_no_adapter"
                last_step   = $step
            }
            exit 2
        }
        break
    }

    Start-Sleep -Seconds $PollSeconds
}

Write-Status @{
    schema        = "myeongri_interpret_watch_v1"
    updated_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    phase         = "interpret_eval"
    adapter_ready = $true
    eval_limit    = $EvalLimit
}

$evalLog = Join-Path $Root "reports/myeongri_interpret_eval_external.log"
$evalErr = Join-Path $Root "reports/myeongri_interpret_eval_external.err.log"
$evalReport = Join-Path $Root "reports/myeongri_interpret_lora_inference_eval_post_train_v1.json"

$evalArgs = @(
    "scripts/run_myeongri_interpret_lora_inference_eval_v1.py",
    "--adapter-path", $adapterPath,
    "--limit", "$EvalLimit",
    "--report-json", $evalReport,
    "--predictions-jsonl", (Join-Path $Root "reports/myeongri_interpret_lora_predictions_post_train_v1.jsonl")
)

"eval start $(Get-Date -Format o)" | Add-Content $watchLog
$p = Start-Process -FilePath "py" -ArgumentList $evalArgs -WorkingDirectory $Root -PassThru -Wait -NoNewWindow `
    -RedirectStandardOutput $evalLog -RedirectStandardError $evalErr
$evalRc = $p.ExitCode
"eval exit $evalRc $(Get-Date -Format o)" | Add-Content $watchLog

Write-Status @{
    schema        = "myeongri_interpret_watch_v1"
    updated_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    phase         = if ($evalRc -eq 0) { "harness_smoke" } else { "eval_failed" }
    eval_exit     = $evalRc
    eval_report   = "reports/myeongri_interpret_lora_inference_eval_post_train_v1.json"
}

if ($evalRc -ne 0) { exit $evalRc }

$hLog = Join-Path $Root "reports/myeongri_interpret_harness_external.log"
$hErr = Join-Path $Root "reports/myeongri_interpret_harness_external.err.log"
$hArgs = @(
    "scripts/run_myeongri_harness_v2_engine_interpret_smoke_v1.py",
    "--limit", "$HarnessLimit",
    "--run-llm",
    "--adapter-path", $adapterPath
)

"harness start $(Get-Date -Format o)" | Add-Content $watchLog
$p2 = Start-Process -FilePath "py" -ArgumentList $hArgs -WorkingDirectory $Root -PassThru -Wait -NoNewWindow `
    -RedirectStandardOutput $hLog -RedirectStandardError $hErr
$harnessRc = $p2.ExitCode
"harness exit $harnessRc $(Get-Date -Format o)" | Add-Content $watchLog

$resolutionRc = 0
if ($evalRc -eq 0) {
    $p3 = Start-Process -FilePath "py" -ArgumentList @(
        "scripts/apply_pack0b_plan_b_after_qwen_v1.py",
        "--eval-json", $evalReport
    ) -WorkingDirectory $Root -PassThru -Wait -NoNewWindow
    $resolutionRc = $p3.ExitCode
}

Write-Status @{
    schema          = "myeongri_interpret_watch_v1"
    updated_utc     = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    phase           = if ($harnessRc -eq 0) { "done" } else { "harness_failed" }
    eval_exit       = $evalRc
    harness_exit    = $harnessRc
    resolution_exit = $resolutionRc
    eval_report     = "reports/myeongri_interpret_lora_inference_eval_post_train_v1.json"
    harness_report  = "reports/myeongri_harness_v2_engine_interpret_smoke_v1_latest.json"
    hypothesis_tier = "B"
}

exit $(if ($harnessRc -ne 0) { $harnessRc } else { $evalRc })
