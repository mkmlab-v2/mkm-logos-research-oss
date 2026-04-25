param(
    [switch]$SkipEnvSync,
    [switch]$SkipTaskRegister,
    [switch]$ExcludeConstitutionGates,
    [switch]$ExcludeReadinessConstitutionRequirement,
    [switch]$ExcludeReadinessStrictRequirement,
    [switch]$IncludeReadiness,
    [switch]$IncludeWebhookSmoke,
    [switch]$IncludeBitcoinTradingOtelSmoke,
    [string]$TrackaDefaultLane = "c3_domain_gated"
)

$ErrorActionPreference = "Stop"
$ops = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal"

if (-not $SkipEnvSync) {
    $sync = Join-Path $ops "sync_required_env_to_user.ps1"
    Write-Host "=== OPS: sync .env -> User env (OPS_ALARM_WEBHOOK_URL, N8N_*, ...) ==="
    & powershell -NoProfile -ExecutionPolicy Bypass -File $sync
    if ($LASTEXITCODE -ne 0) {
        throw "sync_required_env_to_user failed"
    }
}

if (-not $SkipTaskRegister) {
    $reg = Join-Path $ops "register_ops_phase1_chain_task.ps1"
    Write-Host "=== OPS: register daily Phase 1 task (constitution gates on by default) ==="
    if ($ExcludeConstitutionGates) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $reg -ExcludeConstitutionGates -TrackaDefaultLane $TrackaDefaultLane -IncludeBitcoinTradingOtelSmoke:$IncludeBitcoinTradingOtelSmoke
    }
    else {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $reg -TrackaDefaultLane $TrackaDefaultLane -IncludeBitcoinTradingOtelSmoke:$IncludeBitcoinTradingOtelSmoke
    }
    if ($LASTEXITCODE -ne 0) {
        throw "register_ops_phase1_chain_task failed"
    }
}

if ($IncludeReadiness) {
    $vr = Join-Path $ops "verify_ops_phase1_operational_readiness.ps1"
    $requireConstitution = (-not $ExcludeConstitutionGates)
    if ($ExcludeReadinessConstitutionRequirement) { $requireConstitution = $false }
    $requireStrict = (-not $ExcludeReadinessStrictRequirement)
    Write-Host "=== OPS: operational readiness (task TR, report age, alarm URL) ==="
    & $vr -RequireConstitutionGates:$requireConstitution -RequireStrictMode:$requireStrict -RequireBitcoinTradingOtelSmoke:$IncludeBitcoinTradingOtelSmoke
    if ($LASTEXITCODE -ne 0) {
        throw "verify_ops_phase1_operational_readiness failed"
    }
}

if ($IncludeWebhookSmoke) {
    $sm = Join-Path $ops "smoke_ops_phase1_webhook.ps1"
    Write-Host "=== OPS: smoke POST to OPS_ALARM_WEBHOOK_URL ==="
    & powershell -NoProfile -ExecutionPolicy Bypass -File $sm
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_ops_phase1_webhook failed"
    }
}

if ($IncludeBitcoinTradingOtelSmoke) {
    $health = "C:\workspace\scripts\run_workspace_automation_health.ps1"
    Write-Host "=== OPS: bitcoin-trading OTel smoke (health shortcut profile) ==="
    & powershell -NoProfile -ExecutionPolicy Bypass -File $health -WorkspaceRoot "C:\workspace" -BitcoinTradingOtelSmokeOnly
    if ($LASTEXITCODE -ne 0) {
        throw "run_workspace_automation_health (BitcoinTradingOtelSmokeOnly) failed"
    }
}

Write-Host "[bootstrap_ops_phase1_daily] Done."
exit 0
