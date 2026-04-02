param(
    [switch]$IncludeVerifyAllGreen,
    [switch]$SkipFusionStatusCheck,
    [switch]$Strict,
    [switch]$IncludeConstitutionGates,
    [switch]$SkipOpsAlarm
)

$ErrorActionPreference = "Stop"

$ops = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal"
$reportPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_phase1_chain_report_latest.json"
$snapshotPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_environment_snapshot_latest.json"
$fusionStatusPath = "C:\workspace\docs\final\artifacts\ops_fusion_cycle_status_latest.json"
$allGreenPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\all_green_latest.json"

function Get-SharedVaultReachability {
    param([string]$SnapPath)
    $detail = [ordered]@{
        g_drive_root   = $null
        g_vault_probe  = $null
        g_vault_path   = $null
    }
    $level = "unknown"
    if (-not (Test-Path -LiteralPath $SnapPath)) {
        return @{ level = $level; detail = $detail; policy_note = "snapshot_file_missing" }
    }
    try {
        $snap = Get-Content -LiteralPath $SnapPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($snap.PSObject.Properties.Name -contains "g_drive_root") {
            $detail["g_drive_root"] = [bool]$snap.g_drive_root
        }
        if ($snap.PSObject.Properties.Name -contains "g_vault_probe") {
            $detail["g_vault_probe"] = [bool]$snap.g_vault_probe
        }
        if ($snap.PSObject.Properties.Name -contains "g_vault_path") {
            $detail["g_vault_path"] = [string]$snap.g_vault_path
        }
        $rootOk = $detail["g_drive_root"]
        $vaultOk = $detail["g_vault_probe"]
        if ($null -eq $rootOk -or $null -eq $vaultOk) {
            $level = "unknown"
        }
        elseif ($rootOk -and $vaultOk) {
            $level = "ok"
        }
        else {
            $level = "warning"
        }
        return @{ level = $level; detail = $detail; policy_note = "G: optional for core ops; see ops_environment_snapshot_latest.json. Warning does not stop chain." }
    }
    catch {
        return @{ level = "unknown"; detail = $detail; policy_note = "snapshot_parse_error" }
    }
}

function Write-Phase1Report {
    param(
        [int]$SnapshotExit,
        [bool]$FusionSkipped,
        [object]$FusionExit,
        [object]$VerifyExit,
        [bool]$IncludeAllGreen,
        [bool]$StrictMode,
        [string]$Outcome
    )
    $overallOk = ($Outcome -eq "success")
    $sv = Get-SharedVaultReachability -SnapPath $snapshotPath
    $payload = [ordered]@{
        schema = "ops_phase1_chain_report_v1"
        ts_utc = [DateTimeOffset]::UtcNow.ToString("o")
        runner = "projects/bitcoin-trading/ops/windows-rehearsal/run_ops_phase1_chain.ps1"
        scope_note = "Operational runbook snapshots and gates only; not constitutional interpretation or autonomous strategy changes."
        snapshot_exit_code = $SnapshotExit
        shared_vault_reachability = $sv.level
        shared_vault_probe = $sv.detail
        shared_vault_policy_note = $sv.policy_note
        fusion_check_skipped = $FusionSkipped
        fusion_exit_code = $FusionExit
        fusion_ok = if ($FusionSkipped) { $null } else { ($FusionExit -eq 0) }
        include_verify_all_green = $IncludeAllGreen
        verify_all_green_exit_code = $VerifyExit
        verify_all_green_ok = if (-not $IncludeAllGreen) { $null } else { ($VerifyExit -eq 0) }
        strict_mode = $StrictMode
        outcome = $Outcome
        overall_chain_ok = $overallOk
        artifacts = [ordered]@{
            environment_snapshot = $snapshotPath
            ops_fusion_cycle_status = $fusionStatusPath
            all_green_latest = $allGreenPath
            phase1_chain_report = $reportPath
        }
    }
    $parent = Split-Path -Parent $reportPath
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Write-Host ("[phase1] WROTE report: {0}" -f $reportPath)
    if ($sv.level -eq "warning") {
        Write-Host "[phase1] WARN shared vault (G:) not fully reachable - core chain status unchanged; see shared_vault_* in report." -ForegroundColor Yellow
    }
}

function Send-OpsPhase1Webhook {
    param(
        [Parameter(Mandatory = $true)][string]$Kind,
        [Parameter(Mandatory = $true)][string]$Message
    )
    if ($SkipOpsAlarm) { return }
    $url = [Environment]::GetEnvironmentVariable("OPS_ALARM_WEBHOOK_URL", "Process")
    if ([string]::IsNullOrWhiteSpace($url)) {
        $url = [Environment]::GetEnvironmentVariable("OPS_ALARM_WEBHOOK_URL", "User")
    }
    if ([string]::IsNullOrWhiteSpace($url)) {
        $url = [Environment]::GetEnvironmentVariable("OPS_ALARM_WEBHOOK_URL", "Machine")
    }
    if ([string]::IsNullOrWhiteSpace($url)) { return }
    try {
        $bodyObj = [ordered]@{
            event       = "ops_phase1_chain"
            kind        = $Kind
            message     = $Message
            report_path = $reportPath
            ts_utc      = [DateTimeOffset]::UtcNow.ToString("o")
        }
        $json = $bodyObj | ConvertTo-Json -Compress -Depth 5
        Invoke-RestMethod -Uri $url -Method Post -Body $json -ContentType "application/json; charset=utf-8" -TimeoutSec 30
        Write-Host ("[phase1] Webhook sent ({0})" -f $Kind)
    }
    catch {
        Write-Host ("[phase1] WARN webhook post failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
    }
}

Write-Host "=== Phase 1 chain: environment snapshot ==="
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ops "collect_ops_environment_snapshot.ps1")
    $snapshotExit = $LASTEXITCODE
    if ($snapshotExit -ne 0) {
        Write-Phase1Report -SnapshotExit $snapshotExit -FusionSkipped $true -FusionExit $null -VerifyExit $null -IncludeAllGreen $false -StrictMode $Strict -Outcome "snapshot_failed"
        throw "collect_ops_environment_snapshot failed"
    }

    $fusionSkipped = [bool]$SkipFusionStatusCheck
    $fusionExit = $null
    Write-Host "=== Phase 1 chain: fusion status (ops overall_ok) ==="
    if (-not $SkipFusionStatusCheck) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ops "verify_ops_fusion_cycle_status.ps1")
        $fusionExit = $LASTEXITCODE
        if ($fusionExit -ne 0) {
            $msg = "[phase1] fusion status check failed — run run_ops_fusion_cycle.ps1 if stale, then re-check."
            if ($Strict) {
                Write-Phase1Report -SnapshotExit $snapshotExit -FusionSkipped $false -FusionExit $fusionExit -VerifyExit $null -IncludeAllGreen $IncludeVerifyAllGreen -StrictMode $true -Outcome "fusion_failed_strict"
                throw $msg
            }
            Write-Host "$msg" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[phase1] Skipped fusion status check (-SkipFusionStatusCheck)"
    }

    $verifyExit = $null
    if ($IncludeVerifyAllGreen) {
        Write-Host "=== Phase 1 chain: verify_all_green (full) ==="
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ops "verify_all_green.ps1")
        $verifyExit = $LASTEXITCODE
        if ($verifyExit -ne 0) {
            Write-Phase1Report -SnapshotExit $snapshotExit -FusionSkipped $fusionSkipped -FusionExit $fusionExit -VerifyExit $verifyExit -IncludeAllGreen $true -StrictMode $Strict -Outcome "verify_all_green_failed"
            throw "verify_all_green failed"
        }
    }

    $outcome = "success"
    if (-not $fusionSkipped -and $fusionExit -ne 0) {
        $outcome = "fusion_warn"
    }
    Write-Phase1Report -SnapshotExit $snapshotExit -FusionSkipped $fusionSkipped -FusionExit $fusionExit -VerifyExit $verifyExit -IncludeAllGreen $IncludeVerifyAllGreen -StrictMode $Strict -Outcome $outcome

    if ($IncludeConstitutionGates) {
        Write-Host "=== Phase 1 chain: constitution gates (JSON + registry + risk allowlist) ==="
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ops "verify_constitution_gates.ps1")
        $constitutionExit = $LASTEXITCODE
        if ($constitutionExit -ne 0) {
            throw "verify_constitution_gates failed (exit $constitutionExit); see memory/v2/ops/constitution_gates_result_latest.json"
        }
    }

    if (Test-Path -LiteralPath $reportPath) {
        try {
            $rep = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $skipVaultWarn = $false
            foreach ($scope in @("Process", "User", "Machine")) {
                $sw = [Environment]::GetEnvironmentVariable("OPS_ALARM_SKIP_SHARED_VAULT_WARNING", $scope)
                if ($sw -eq "1" -or ($sw -and $sw.ToLowerInvariant() -eq "true")) { $skipVaultWarn = $true; break }
            }
            if ($rep.PSObject.Properties.Name -contains "shared_vault_reachability" -and
                [string]$rep.shared_vault_reachability -eq "warning" -and -not $skipVaultWarn) {
                Send-OpsPhase1Webhook -Kind "shared_vault_warning" -Message "shared_vault_reachability=warning (G: optional; see report)"
            }
        }
        catch {
            Write-Host ("[phase1] WARN could not evaluate shared_vault for webhook: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
        }
    }

    Write-Host ""
    Write-Host "=== Manual (not scriptable here) ==="
    Write-Host "n8n: paste examples/n8n_public_event_whitelist_function.js into Function node; smoke ingest to gateway."
    Write-Host "Unattended: use Task Scheduler UI or schtasks /Change with stored creds; confirm G: after pilot."
    Write-Host "[phase1] Chain finished."
    exit 0
}
catch {
    Send-OpsPhase1Webhook -Kind "failure" -Message $_.Exception.Message
    throw
}
