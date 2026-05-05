param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"

function Step([string]$Name, [scriptblock]$Block) {
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit $LASTEXITCODE)"
    }
}

try {
    $daily = Join-Path $WorkspaceRoot "scripts\Invoke-MkmAiV2DailyReadiness.ps1"
    Step "Daily readiness runner" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $daily -WorkspaceRoot $WorkspaceRoot
    }

    $health = Join-Path $WorkspaceRoot "scripts\run_workspace_automation_health.ps1"
    Step "Health profile (v2 + final + Track C guard)" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $health `
            -WorkspaceRoot $WorkspaceRoot `
            -SkipVaultMirror `
            -SkipMkmMemoryInventory `
            -SkipPhase1Readiness `
            -SkipNewsObservationContractSmoke `
            -IncludeMkmAiV2Readiness `
            -IncludeMkmAiFinalOpsGuard `
            -IncludeMkmAiTrackCHandoffGuard
    }

    $freeze = Join-Path $WorkspaceRoot "scripts\build_mkm_trackc_delivery_freeze_log_v1.py"
    Step "Delivery freeze log" {
        & py $freeze
    }

    $paddleStatus = Join-Path $WorkspaceRoot "scripts\build_paddle_onboarding_status_v1.py"
    Step "Paddle onboarding status" {
        & py $paddleStatus --workspace-root $WorkspaceRoot
    }

    $dashboard = Join-Path $WorkspaceRoot "scripts\build_mkm_trackc_ops_dashboard_v1.py"
    Step "Track C ops dashboard" {
        & py $dashboard
    }

    $dashboardExec = Join-Path $WorkspaceRoot "scripts\build_mkm_trackc_ops_dashboard_exec_v1.py"
    Step "Track C executive dashboard" {
        & py $dashboardExec
    }

    $runbookChecklist = Join-Path $WorkspaceRoot "scripts\build_mkm_trackc_operations_runbook_checklist_v1.py"
    Step "Track C operations runbook checklist" {
        & py $runbookChecklist
    }

    $chatResumePack = Join-Path $WorkspaceRoot "scripts\build_mkm_chat_resume_pack_v1.py"
    Step "Chat resume pack" {
        & py $chatResumePack
    }

    $summary = [ordered]@{
        schema = "mkm_trackc_operational_acceptance_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        workspace_root = $WorkspaceRoot
        status = "PASS"
        evidence = [ordered]@{
            readiness_artifact = "docs/final/artifacts/mkm_ai_v2_readiness_latest.json"
            final_guard_report = "docs/final/artifacts/mkm_ai_final_ops_guard_latest.json"
            trackc_guard_report = "docs/final/artifacts/mkm_trackc_client_handoff_guard_latest.json"
            freeze_log = "docs/final/artifacts/mkm_trackc_delivery_freeze_log_latest.json"
            ops_dashboard = "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json"
            ops_dashboard_exec = "docs/final/artifacts/mkm_trackc_ops_dashboard_exec_latest.md"
            operations_runbook_checklist = "docs/final/artifacts/mkm_trackc_operations_runbook_checklist_latest.md"
            chat_resume_pack = "docs/final/artifacts/mkm_chat_resume_pack_latest.md"
            paddle_onboarding_runbook = "docs/final/artifacts/PADDLE_ONBOARDING_SECURE_RUNBOOK_V1.md"
            paddle_onboarding_status = "docs/final/artifacts/paddle_onboarding_status_latest.json"
        }
    }

    $out = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_trackc_operational_acceptance_latest.json"
    $summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $out -Encoding UTF8

    Write-Host ""
    Write-Host "MKM TRACKC ACCEPTANCE: PASS" -ForegroundColor Green
    Write-Host "artifact: $out"
    exit 0
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
