param(
    [string]$VerifyScriptPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\verify_all_green.ps1",
    [string]$ReconcileScriptPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\reconcile_automation_registry.ps1",
    [string]$VerifyOutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\all_green_latest.json",
    [string]$LoopOutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\all_green_self_heal_latest.json",
    [switch]$SlackNotifyLive,
    [string]$WebhookUrl = "",
    [int]$WebhookTimeoutSec = 10
)

$ErrorActionPreference = "Stop"

function Invoke-Verify([switch]$EnforceRegistry) {
    $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $VerifyScriptPath, "-OutputPath", $VerifyOutputPath)
    if ($EnforceRegistry) {
        $args += "-EnforceRegistry"
    }
    if ($SlackNotifyLive) {
        $args += "-SlackNotifyLive"
    }

    $null = & powershell @args
    $code = $LASTEXITCODE
    return [int]$code
}

function Invoke-ReconcileEnforce {
    $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ReconcileScriptPath, "-Enforce")
    $null = & powershell @args
    $code = $LASTEXITCODE
    return [int]$code
}

function Read-JsonOrNull([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Get-EnvAnyScope([string]$Name) {
    $u = [Environment]::GetEnvironmentVariable($Name, "User")
    if (-not [string]::IsNullOrWhiteSpace($u)) { return $u.Trim() }
    $m = [Environment]::GetEnvironmentVariable($Name, "Machine")
    if (-not [string]::IsNullOrWhiteSpace($m)) { return $m.Trim() }
    $p = [Environment]::GetEnvironmentVariable($Name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($p)) { return $p.Trim() }
    return ""
}

function Get-ResolvedWebhookUrl {
    if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
        return $WebhookUrl.Trim()
    }
    foreach ($name in @("N8N_ALL_GREEN_WEBHOOK_URL", "N8N_WEBHOOK_URL")) {
        $candidate = Get-EnvAnyScope -Name $name
        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            return $candidate
        }
    }
    return ""
}

function Publish-WebhookEvent([string]$EventType, [object]$Payload) {
    $resolved = Get-ResolvedWebhookUrl
    if ([string]::IsNullOrWhiteSpace($resolved)) {
        Write-Host "[all-green-loop] Webhook skipped: URL missing"
        return $false
    }

    try {
        $bodyObj = [ordered]@{
            schema = "all_green_self_heal_event_v1"
            event_type = $EventType
            ts_utc = [DateTimeOffset]::UtcNow.ToString("o")
            payload = $Payload
        }
        $body = $bodyObj | ConvertTo-Json -Depth 10 -Compress
        Invoke-RestMethod -Method Post -Uri $resolved -ContentType "application/json" -Body $body -TimeoutSec $WebhookTimeoutSec | Out-Null
        Write-Host ("[all-green-loop] Webhook sent: {0}" -f $EventType)
        return $true
    } catch {
        Write-Host ("[all-green-loop] WARN: webhook failed ({0})" -f $_.Exception.Message) -ForegroundColor Yellow
        return $false
    }
}

if (-not (Test-Path -LiteralPath $VerifyScriptPath)) {
    throw "verify_all_green script not found: $VerifyScriptPath"
}
if (-not (Test-Path -LiteralPath $ReconcileScriptPath)) {
    throw "reconcile script not found: $ReconcileScriptPath"
}

$reconcileReportPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\automation_registry_reconcile_latest.json"
$attempts = @()
$actionTaken = "none"
$reconcileExit = $null

Write-Host "[all-green-loop] Step 1/3 verify (baseline)"
$firstExit = Invoke-Verify
$firstDoc = Read-JsonOrNull -Path $VerifyOutputPath
$firstOverall = $false
if ($firstDoc -and $firstDoc.overall_ok -eq $true) {
    $firstOverall = $true
}
$attempts += [ordered]@{
    phase = "initial_verify"
    exit_code = $firstExit
    overall_ok = $firstOverall
}

if ($firstExit -eq 0 -and $firstOverall) {
    $summary = [ordered]@{
        status = "pass_without_recovery"
        verify_output_path = $VerifyOutputPath
        loop_output_path = $LoopOutputPath
        attempts = $attempts
    }
    $payload = [ordered]@{
        schema = "all_green_self_heal_loop_v1"
        ts_utc = [DateTimeOffset]::UtcNow.ToString("o")
        ok = $true
        action_taken = $actionTaken
        reconcile_exit_code = $reconcileExit
        reconcile_report_path = $reconcileReportPath
        attempts = $attempts
    }
    $loopParent = Split-Path -Parent $LoopOutputPath
    if ($loopParent -and -not (Test-Path -LiteralPath $loopParent)) {
        New-Item -ItemType Directory -Path $loopParent -Force | Out-Null
    }
    Set-Content -LiteralPath $LoopOutputPath -Value ($payload | ConvertTo-Json -Depth 10) -Encoding UTF8
    Publish-WebhookEvent -EventType "all_green_ok" -Payload $summary | Out-Null
    exit 0
}

Write-Warning "[all-green-loop] verify failed -> enforcing registry reconciliation"
$actionTaken = "reconcile_enforce"
$reconcileExit = Invoke-ReconcileEnforce
$reconcileDoc = Read-JsonOrNull -Path $reconcileReportPath

$attempts += [ordered]@{
    phase = "reconcile_enforce"
    exit_code = $reconcileExit
    all_ok = if ($reconcileDoc) { [bool]$reconcileDoc.all_ok } else { $false }
    drift_count = if ($reconcileDoc) { [int]$reconcileDoc.drift_count } else { $null }
    fixed_count = if ($reconcileDoc) { [int]$reconcileDoc.fixed_count } else { $null }
}

Write-Host "[all-green-loop] Step 3/3 re-verify after recovery"
$secondExit = Invoke-Verify -EnforceRegistry
$secondDoc = Read-JsonOrNull -Path $VerifyOutputPath
$secondOverall = $false
if ($secondDoc -and $secondDoc.overall_ok -eq $true) {
    $secondOverall = $true
}
$attempts += [ordered]@{
    phase = "post_recovery_verify"
    exit_code = $secondExit
    overall_ok = $secondOverall
}

$ok = ($secondExit -eq 0 -and $secondOverall)
$payload = [ordered]@{
    schema = "all_green_self_heal_loop_v1"
    ts_utc = [DateTimeOffset]::UtcNow.ToString("o")
    ok = $ok
    action_taken = $actionTaken
    reconcile_exit_code = $reconcileExit
    reconcile_report_path = $reconcileReportPath
    attempts = $attempts
}

$loopParent = Split-Path -Parent $LoopOutputPath
if ($loopParent -and -not (Test-Path -LiteralPath $loopParent)) {
    New-Item -ItemType Directory -Path $loopParent -Force | Out-Null
}
Set-Content -LiteralPath $LoopOutputPath -Value ($payload | ConvertTo-Json -Depth 10) -Encoding UTF8
Write-Host ("[all-green-loop] saved: {0}" -f $LoopOutputPath)

$eventType = if ($ok) { "all_green_recovered" } else { "all_green_failed_after_recovery" }
$summary = [ordered]@{
    status = $eventType
    verify_output_path = $VerifyOutputPath
    loop_output_path = $LoopOutputPath
    reconcile_report_path = $reconcileReportPath
    attempts = $attempts
}
Publish-WebhookEvent -EventType $eventType -Payload $summary | Out-Null

if ($ok) { exit 0 }
exit 1
