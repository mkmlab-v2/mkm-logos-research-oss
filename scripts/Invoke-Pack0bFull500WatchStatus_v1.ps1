#Requires -Version 5.1
<#
.SYNOPSIS
  Snapshot or poll Pack0-B ordered full500 train status (Run-Pack0bOrderedTrain_v1.ps1).

.EXAMPLE
  pwsh -NoProfile -File scripts/Invoke-Pack0bFull500WatchStatus_v1.ps1 -Once

.EXAMPLE
  pwsh -NoProfile -File scripts/Invoke-Pack0bFull500WatchStatus_v1.ps1 -PollSeconds 120
#>
param(
    [switch]$Once,
    [int]$PollSeconds = 120
)

$ErrorActionPreference = "Stop"
$Root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT } else { "C:\workspace" }
Set-Location $Root

$log = Join-Path $Root "reports/pack0b_ordered_train_v1.log"
$lock = Join-Path $Root "reports/pack0b_ordered_train_v1.lock"
$adapterDir = Join-Path $Root "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_full500_v1"
$statusJson = Join-Path $Root "reports/pack0b_full500_ordered_watch_latest.json"
$evalReport = Join-Path $Root "reports/myeongri_deterministic_lora_locked_eval_inference_eval_latest.json"

function Get-TrainPid {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -match "train_mkm_prophecy_lora_windows" -and
            $_.CommandLine -match "run_pack0b_full500_v1"
        } |
        Select-Object -ExpandProperty ProcessId -First 1
}

function Get-LastStep {
    if (-not (Test-Path -LiteralPath $log)) { return $null }
    $m = Select-String -Path $log -Pattern "(\d+)/500" -AllMatches | Select-Object -Last 1
    if ($m -and $m.Matches.Count -gt 0) { return [int]$m.Matches[-1].Groups[1].Value }
    return $null
}

function Get-LatestCheckpoint {
    if (-not (Test-Path -LiteralPath $adapterDir)) { return $null }
    $dirs = Get-ChildItem -Path $adapterDir -Directory -Filter "checkpoint-*" -ErrorAction SilentlyContinue |
        Sort-Object { [int]($_.Name -replace "checkpoint-", "") } -Descending
    if ($dirs) { return $dirs[0].Name }
    return $null
}

function Get-GpuSnapshot {
    try {
        $line = & nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>$null | Select-Object -First 1
        if (-not $line) { return $null }
        $parts = $line -split ",\s*"
        if ($parts.Count -ge 3) {
            return @{
                utilization_pct = [int]$parts[0]
                memory_used_mib = [int]$parts[1]
                memory_total_mib  = [int]$parts[2]
            }
        }
    }
    catch { }
    return $null
}

function Write-Status {
    param([hashtable]$Doc)
    $Doc | ConvertTo-Json -Depth 6 | Set-Content -Path $statusJson -Encoding utf8
}

function Build-Status {
    $trainPid = Get-TrainPid
    $alive = $false
    if ($trainPid) {
        $alive = $null -ne (Get-Process -Id $trainPid -ErrorAction SilentlyContinue)
    }
    $step = Get-LastStep
    $done = $false
    $failed = $false
    if (Test-Path -LiteralPath $log) {
        $tail = Get-Content -LiteralPath $log -Tail 40 -ErrorAction SilentlyContinue
        $done = $tail -match "=== DONE ordered pipeline exit=0 ==="
        $failed = $tail -match "train failed \(full500\)"
    }
    $phase = "idle"
    if ($failed) { $phase = "failed" }
    elseif ($done) { $phase = "done" }
    elseif ($alive -or ($null -ne $step -and $step -lt 500)) { $phase = "training" }

    return @{
        schema           = "pack0b_full500_ordered_watch_v1"
        updated_utc      = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        phase            = $phase
        max_steps        = 500
        last_step        = $step
        resume_checkpoint = Get-LatestCheckpoint
        train_pid        = $trainPid
        train_alive      = $alive
        lock_present     = Test-Path -LiteralPath $lock
        ordered_log      = "reports/pack0b_ordered_train_v1.log"
        adapter_dir      = "storage/adapters/myeongri_deterministic_lora_v0/run_pack0b_full500_v1"
        eval_report      = "reports/myeongri_deterministic_lora_locked_eval_inference_eval_latest.json"
        gpu              = Get-GpuSnapshot
    }
}

do {
    $doc = Build-Status
    Write-Status $doc
    Write-Host ("[pack0b-watch] phase={0} step={1}/500 ckpt={2} gpu={3}%" -f $doc.phase, $doc.last_step, $doc.resume_checkpoint, $(if ($doc.gpu) { $doc.gpu.utilization_pct } else { "?" }))

    if ($Once -or $doc.phase -eq "done" -or $doc.phase -eq "failed") { break }
    Start-Sleep -Seconds $PollSeconds
} while ($true)

if ($doc.phase -eq "failed") { exit 2 }
exit 0
