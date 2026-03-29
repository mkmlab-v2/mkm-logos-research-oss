#Requires -Version 5.1
<#
.SYNOPSIS
  Run a repo GPU workload with stdout/stderr tee'd to logs/gpu_runs/ (logs/ is gitignored).

.DESCRIPTION
  - Optional pre-flight: nvidia-smi temperature.gpu vs -MaxTempC (default 85).
  - Does NOT install PM2; on Windows use Task Scheduler to call this script, or pm2 if you already use it.
  - Example (short dev run, from repo root in PowerShell):
      .\scripts\run_gpu_job_windows.ps1 -SkipTempCheck -PyArgs @('--ks','100','--limit','50')
  - Example (full sweep — long; writes checkpoint in backtest_results, auto-resumes if interrupted):
      .\scripts\run_gpu_job_windows.ps1 -PyArgs @()
  - Discard old checkpoint and run all ks from scratch:
      .\scripts\run_gpu_job_windows.ps1 -PyArgs @('--fresh')

.NOTES
  Real training entrypoints in this repo are scripts like sweep_logos_regime_topk_btc_ext.py
  and bench_logos_gpu_corpus.py — there is no scripts/train_logos_resonance.py.
  sweep_logos_regime_topk_btc_ext: default is full ks list (no early stop). Checkpoint file:
  backtest_results/<prefix>_SWEEP_CHECKPOINT.json — same command line after a crash resumes remaining k.
#>
param(
    [string]$PythonScript = "scripts\sweep_logos_regime_topk_btc_ext.py",
    [string[]]$PyArgs = @(),
    [int]$MaxTempC = 85,
    [switch]$SkipTempCheck
)

$ErrorActionPreference = "Stop"
# Always derive repo root from this script's location (avoids accidental positional bind to numeric args).
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$LogDir = Join-Path $RepoRoot "logs\gpu_runs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$JobName = [System.IO.Path]::GetFileNameWithoutExtension($PythonScript)
$LogFile = Join-Path $LogDir "gpu_run_${JobName}_${Stamp}.log"

function Write-LogLine {
    param([string]$Line)
    $Line | Tee-Object -FilePath $LogFile -Append
}

Write-LogLine "=== gpu run start $(Get-Date -Format o) ==="
Write-LogLine "repo: $RepoRoot"
Write-LogLine "script: $PythonScript args: $($PyArgs -join ' ')"

if (-not $SkipTempCheck) {
    $smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if (-not $smi) {
        Write-LogLine "WARN: nvidia-smi not in PATH; temperature check skipped."
    } else {
        $snap = & nvidia-smi -q -d TEMPERATURE 2>&1 | Out-String
        Write-LogLine "--- nvidia-smi temperature (query) ---"
        Write-LogLine $snap
        $csv = & nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>&1
        $first = ($csv | Select-Object -First 1).ToString().Trim()
        if ($first -match '^\d+$') {
            $t = [int]$first
            Write-LogLine "GPU temperature.gpu (first device): ${t}C (MaxTempC=$MaxTempC)"
            if ($t -gt $MaxTempC) {
                Write-LogLine "ABORT: temperature above MaxTempC."
                exit 2
            }
        } else {
            Write-LogLine "WARN: could not parse temperature from nvidia-smi; continuing."
        }
    }
}

$pyPath = Join-Path $RepoRoot $PythonScript
if (-not (Test-Path -LiteralPath $pyPath)) {
    Write-LogLine "ERROR: script not found: $pyPath"
    exit 1
}

$exit = 0
try {
    & py -u $pyPath @PyArgs 2>&1 | ForEach-Object { Write-LogLine $_ }
    if ($LASTEXITCODE -ne 0) { $exit = $LASTEXITCODE }
} catch {
    Write-LogLine "ERROR: $($_.Exception.Message)"
    $exit = 1
}

Write-LogLine "=== gpu run end $(Get-Date -Format o) exit=$exit ==="
Write-LogLine "log file: $LogFile"
exit $exit
