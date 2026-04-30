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
    $policyPath = Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_4agent_monitor_policy_v1.json"
    if (-not (Test-Path -LiteralPath $policyPath)) {
        throw "missing monitor policy: $policyPath"
    }
    $policy = Get-Content -LiteralPath $policyPath -Raw | ConvertFrom-Json
    $gatePath = Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_4agent_promotion_gate_latest.json"
    if (-not (Test-Path -LiteralPath $gatePath)) {
        throw "missing promotion gate: $gatePath"
    }
    $gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
    $gateApproved = ([string]$gate.decision -eq "A_TRACK_PROMOTED_WITH_HUMAN_APPROVAL")

    $bridge = Join-Path $WorkspaceRoot "scripts\run_sasang_4agent_tracka_bridge_v1.py"
    if ($gateApproved) {
        Run-Step "Track A controlled bridge refresh" {
            & py $bridge --shadow-ratio 0.1 --max-live-risk-fraction 0.05
        }
    } else {
        Write-Host ""
        Write-Host "=== Track A controlled bridge refresh (skipped: gate not approved) ===" -ForegroundColor Yellow
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
    $autoInjectionEnabled = $false
    $autoForceHold = $false
    $autoReduceExposure = $false
    if ($null -ne $policy.auto_injection) {
        $autoInjectionEnabled = [bool]$policy.auto_injection.enabled
        $autoForceHold = [bool]$policy.auto_injection.force_hold
        $autoReduceExposure = [bool]$policy.auto_injection.reduce_exposure
    }
    $geumhwaBreach = $false
    $geumhwaScore = 0.0
    if ($null -ne $snapshot.metrics -and $null -ne $snapshot.metrics.geumhwa_threshold_breached) {
        $geumhwaBreach = [bool]$snapshot.metrics.geumhwa_threshold_breached
    }
    if ($null -ne $snapshot.metrics -and $null -ne $snapshot.metrics.geumhwa_transition_score) {
        $geumhwaScore = [double]$snapshot.metrics.geumhwa_transition_score
    }
    $cooldownBars = 3
    if ($null -ne $policy.cooldown_bars) {
        $cooldownBars = [int]$policy.cooldown_bars
    }
    $hysteresisConsecutive = 2
    $hysteresisRelease = 0.5
    if ($null -ne $policy.hysteresis) {
        if ($null -ne $policy.hysteresis.consecutive_breach_required) {
            $hysteresisConsecutive = [int]$policy.hysteresis.consecutive_breach_required
        }
        if ($null -ne $policy.hysteresis.release_threshold) {
            $hysteresisRelease = [double]$policy.hysteresis.release_threshold
        }
    }
    $statePath = Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_4agent_auto_injection_state_latest.json"
    $state = $null
    if (Test-Path -LiteralPath $statePath) {
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    }
    $lastInjectionAt = $null
    if ($null -ne $state -and $null -ne $state.last_injection_utc) {
        try { $lastInjectionAt = [datetime]::Parse($state.last_injection_utc) } catch { $lastInjectionAt = $null }
    }
    $consecutiveBreaches = 0
    if ($null -ne $state -and $null -ne $state.consecutive_breaches) {
        $consecutiveBreaches = [int]$state.consecutive_breaches
    }
    if ($geumhwaBreach) {
        $consecutiveBreaches += 1
    } elseif ($geumhwaScore -lt $hysteresisRelease) {
        $consecutiveBreaches = 0
    }
    $cooldownActive = $false
    if ($null -ne $lastInjectionAt) {
        $elapsedHours = ((Get-Date).ToUniversalTime() - $lastInjectionAt.ToUniversalTime()).TotalHours
        if ($elapsedHours -lt $cooldownBars) {
            $cooldownActive = $true
        }
    }
    $hysteresisReady = ($consecutiveBreaches -ge $hysteresisConsecutive)
    $handledByGeumhwaAutoForceHold = ($autoInjectionEnabled -and $geumhwaBreach -and $autoForceHold)
    if (($snapshot.alert -eq $true) -and (-not $handledByGeumhwaAutoForceHold)) {
        $forceHold = Join-Path $WorkspaceRoot "scripts\invoke_sasang_4agent_force_hold_v1.py"
        Run-Step "Auto FORCE_HOLD on alert" {
            & py $forceHold --reason "daily_monitor_alert_autohold"
        }
    }
    $injectionAction = "NONE"
    if ($autoInjectionEnabled -and $geumhwaBreach -and $hysteresisReady -and (-not $cooldownActive)) {
        if ($autoForceHold) {
            $forceHold = Join-Path $WorkspaceRoot "scripts\invoke_sasang_4agent_force_hold_v1.py"
            Run-Step "Auto FORCE_HOLD on geumhwa breach" {
                & py $forceHold --reason "daily_monitor_geumhwa_autoinjection"
            }
        }
        if ($autoForceHold -and $autoReduceExposure) {
            $injectionAction = "FORCE_HOLD_AND_REDUCE_EXPOSURE"
        } elseif ($autoForceHold) {
            $injectionAction = "FORCE_HOLD"
        } elseif ($autoReduceExposure) {
            $injectionAction = "REDUCE_EXPOSURE"
        }
    }

    $injectionArtifact = Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_4agent_auto_injection_latest.json"
    $injectionPayload = [ordered]@{
        schema = "sasang_4agent_auto_injection_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        policy_ref = "docs/final/artifacts/sasang_4agent_monitor_policy_v1.json"
        geumhwa_threshold_breached = [bool]$geumhwaBreach
        geumhwa_transition_score = [double]$geumhwaScore
        auto_injection_enabled = [bool]$autoInjectionEnabled
        hysteresis_ready = [bool]$hysteresisReady
        cooldown_active = [bool]$cooldownActive
        action = $injectionAction
        human_reactivation_required = [bool]$policy.human_reactivation_required
    }
    $injectionPayload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $injectionArtifact -Encoding UTF8
    $newState = [ordered]@{
        schema = "sasang_4agent_auto_injection_state_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        consecutive_breaches = [int]$consecutiveBreaches
        hysteresis_consecutive_required = [int]$hysteresisConsecutive
        hysteresis_release_threshold = [double]$hysteresisRelease
        cooldown_bars = [int]$cooldownBars
        cooldown_active = [bool]$cooldownActive
        last_injection_utc = if ($injectionAction -ne "NONE") { (Get-Date).ToUniversalTime().ToString("o") } elseif ($null -ne $lastInjectionAt) { $lastInjectionAt.ToUniversalTime().ToString("o") } else { $null }
    }
    $newState | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statePath -Encoding UTF8

    $out = Join-Path $WorkspaceRoot "docs\final\artifacts\sasang_4agent_daily_monitor_run_latest.json"
    $payload = [ordered]@{
        schema = "sasang_4agent_daily_monitor_run_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        workspace_root = $WorkspaceRoot
        alert = [bool]$snapshot.alert
        recommended_action = [string]$snapshot.recommended_action
        monitor_snapshot_ref = "docs/final/artifacts/sasang_4agent_monitor_snapshot_latest.json"
        monitor_policy_ref = "docs/final/artifacts/sasang_4agent_monitor_policy_v1.json"
        auto_injection_ref = "docs/final/artifacts/sasang_4agent_auto_injection_latest.json"
        auto_injection_state_ref = "docs/final/artifacts/sasang_4agent_auto_injection_state_latest.json"
        auto_injection_action = $injectionAction
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

