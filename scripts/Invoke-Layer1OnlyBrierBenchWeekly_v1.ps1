<#
.SYNOPSIS
  Weekly Layer-1-only Brier bench PoC routine (register, live probe, sync, eval).

.DESCRIPTION
  B-track only; no Track A bridge. Appends JSONL audit line to
  reports/layer1_only_brier_bench_weekly_log.jsonl.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipRegister,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$reportsDir = Join-Path $WorkspaceRoot "reports"
$logPath = Join-Path $reportsDir "layer1_only_brier_bench_weekly_log.jsonl"
$chain = Join-Path $WorkspaceRoot "scripts\run_layer1_only_brier_bench_chain_v1.py"
$register = Join-Path $WorkspaceRoot "scripts\register_layer1_only_brier_bench_poc_v1.py"

if (-not (Test-Path -LiteralPath $chain)) {
    throw "Missing chain script: $chain"
}
if (-not (Test-Path -LiteralPath $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}

$started = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$exitCode = 0
$steps = @()
$err = $null

function Invoke-Step([string]$Name, [string[]]$PyArgs) {
    $proc = Start-Process -FilePath "py" -ArgumentList $PyArgs -WorkingDirectory $WorkspaceRoot -Wait -PassThru -NoNewWindow
    $script:steps += @{ step = $Name; exit_code = $proc.ExitCode }
    if ($proc.ExitCode -ne 0) {
        $script:exitCode = $proc.ExitCode
        throw "Step failed ($Name) exit=$($proc.ExitCode)"
    }
}

try {
    if (-not $SkipRegister) {
        $regArgs = @($register)
        if ($DryRun) { $regArgs += "--dry-run" }
        Invoke-Step "register" $regArgs
    }

    $chainArgs = @($chain, "--live")
    if ($SkipRegister) { $chainArgs += "--skip-register" }
    if ($DryRun) { $chainArgs += "--dry-run" }
    Invoke-Step "chain" $chainArgs
} catch {
    $err = $_.Exception.Message
} finally {
    $finished = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $row = [ordered]@{
        schema = "layer1_only_brier_bench_weekly_log_v1"
        started_at_utc = $started
        finished_at_utc = $finished
        track_wall = "B"
        auto_bridge_to_a = $false
        dry_run = [bool]$DryRun
        skip_register = [bool]$SkipRegister
        exit_code = $exitCode
        steps = $steps
    }
    if ($err) { $row.error = $err }
    ($row | ConvertTo-Json -Compress) + "`n" | Add-Content -LiteralPath $logPath -Encoding utf8
}

if ($exitCode -ne 0) {
    Write-Error $err
    exit $exitCode
}

Write-Host "[OK] Layer-1 Brier bench weekly routine complete. Log: $logPath"
