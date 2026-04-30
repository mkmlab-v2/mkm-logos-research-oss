param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"

function Run-Step([string]$Name, [scriptblock]$Block) {
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit $LASTEXITCODE)"
    }
}

try {
    $bridge = Join-Path $WorkspaceRoot "scripts\run_sasang_4agent_tracka_bridge_v1.py"
    Run-Step "Track A controlled bridge refresh" {
        & py $bridge --shadow-ratio 0.1 --max-live-risk-fraction 0.05
    }

    $monitor = Join-Path $WorkspaceRoot "scripts\build_sasang_4agent_monitor_snapshot_v1.py"
    Run-Step "Monitor snapshot build" {
        & py $monitor
    }

    $snapshotPath = Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_4agent_monitor_snapshot_latest.json"
    if (-not (Test-Path -LiteralPath $snapshotPath)) {
        throw "missing monitor snapshot: $snapshotPath"
    }
    $snapshot = Get-Content -LiteralPath $snapshotPath -Raw | ConvertFrom-Json
    if ($snapshot.alert -eq $true) {
        $forceHold = Join-Path $WorkspaceRoot "scripts\invoke_sasang_4agent_force_hold_v1.py"
        Run-Step "Auto FORCE_HOLD on alert" {
            & py $forceHold --reason "daily_monitor_alert_autohold"
        }
    }

    $out = Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_4agent_daily_monitor_run_latest.json"
    $payload = [ordered]@{
        schema = "sasang_4agent_daily_monitor_run_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        workspace_root = $WorkspaceRoot
        alert = [bool]$snapshot.alert
        recommended_action = [string]$snapshot.recommended_action
        monitor_snapshot_ref = "docs/final/artifacts/sasang_4agent_monitor_snapshot_latest.json"
        bridge_ref = "docs/final/artifacts/sasang_4agent_tracka_bridge_latest.json"
        promotion_gate_ref = "docs/final/artifacts/sasang_4agent_promotion_gate_latest.json"
        status = if ($snapshot.alert) { "PASS_WITH_AUTO_HOLD" } else { "PASS" }
    }
    $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $out -Encoding UTF8

    Write-Host ""
    Write-Host "SASANG 4-AGENT DAILY MONITOR: $($payload.status)" -ForegroundColor Green
    Write-Host "artifact: $out"
    exit 0
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

