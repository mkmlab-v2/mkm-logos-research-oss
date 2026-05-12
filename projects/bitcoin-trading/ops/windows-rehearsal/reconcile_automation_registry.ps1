param(
    [string]$RegistryPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\automation_registry.json",
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\automation_registry_reconcile_latest.json",
    [switch]$Enforce,
    [switch]$ShowJson,
    [switch]$IgnoreExecutionHealth
)

$ErrorActionPreference = "Stop"

function Get-TaskSnapshot([string]$TaskName) {
    # Prefer ScheduledTasks cmdlets to avoid locale-dependent parsing from schtasks output.
    try {
        $queryName = $TaskName
        $queryPath = "\"
        if ($TaskName -match "^\\") {
            $trimmed = $TaskName.TrimStart("\")
            $idx = $trimmed.LastIndexOf("\")
            if ($idx -ge 0) {
                $queryPath = "\" + $trimmed.Substring(0, $idx + 1)
                $queryName = $trimmed.Substring($idx + 1)
            } else {
                $queryName = $trimmed
            }
        }
        $task = Get-ScheduledTask -TaskName $queryName -TaskPath $queryPath -ErrorAction Stop
        $info = Get-ScheduledTaskInfo -TaskName $queryName -TaskPath $queryPath -ErrorAction Stop
        return @{
            task_name = $TaskName
            exists = $true
            status = [string]$task.State
            next_run_time = [string]$info.NextRunTime
            last_result = [string]$info.LastTaskResult
        }
    }
    catch {
        return @{
            task_name = $TaskName
            exists = $false
            status = "NOT_FOUND"
            next_run_time = ""
            last_result = ""
        }
    }
}

function Normalize-Status([string]$status) {
    if ([string]::IsNullOrWhiteSpace($status)) { return "Unknown" }
    $s = $status.Trim().ToLowerInvariant()
    if ($s -eq "running") { return "Running" }
    if ($s -eq "ready") { return "Ready" }
    if ($s -eq "disabled") { return "Disabled" }
    return $status.Trim()
}

function Is-LastResultSuccess([string]$value) {
    if ([string]::IsNullOrWhiteSpace($value)) { return $false }
    $v = $value.Trim().ToLowerInvariant()
    if ($v -eq "0") { return $true }
    if ($v -eq "0x0") { return $true }
    if ($v -eq "the operation completed successfully. (0x0)") { return $true }
    return $false
}

if (-not (Test-Path -LiteralPath $RegistryPath)) {
    throw "Registry not found: $RegistryPath"
}
$registry = Get-Content -LiteralPath $RegistryPath -Raw -Encoding utf8 | ConvertFrom-Json
if (-not $registry.tasks) {
    throw "Registry has no tasks: $RegistryPath"
}

$items = @()
$driftCount = 0
$fixedCount = 0
$executionIssueCount = 0
foreach ($t in $registry.tasks) {
    $name = [string]$t.name
    $expected = Normalize-Status ([string]$t.expected_status)
    $optional = $false
    if ($t.PSObject.Properties.Name -contains "optional") {
        $optional = [bool]$t.optional
    }
    $snap = Get-TaskSnapshot -TaskName $name
    $actual = Normalize-Status ([string]$snap.status)
    $drift = $true
    if (($expected -eq "Ready" -and ($actual -in @("Ready", "Running"))) -or ($expected -eq $actual)) {
        $drift = $false
    }

    $skippedOptionalMissing = ($optional -and (-not $snap.exists))
    if ($skippedOptionalMissing) {
        # Optional deck: missing task is not drift (machine may not have registered extended automation).
        $drift = $false
    }

    $action = "none"
    $enforcedOk = $null
    if ($Enforce -and $snap.exists -and $drift -and -not $skippedOptionalMissing) {
        if ($expected -eq "Disabled") {
            schtasks /Change /TN $name /DISABLE > $null 2>&1
            $action = "disable"
            $enforcedOk = ($LASTEXITCODE -eq 0)
        } elseif ($expected -eq "Ready") {
            schtasks /Change /TN $name /ENABLE > $null 2>&1
            $action = "enable"
            $enforcedOk = ($LASTEXITCODE -eq 0)
        } else {
            $action = "unsupported_expected_status"
            $enforcedOk = $false
        }
        if ($enforcedOk) {
            $fixedCount += 1
            $snap2 = Get-TaskSnapshot -TaskName $name
            $actual = Normalize-Status ([string]$snap2.status)
            $drift = -not (
                ($expected -eq "Ready" -and ($actual -in @("Ready", "Running"))) -or
                ($expected -eq $actual)
            )
        }
    }

    if ($drift) { $driftCount += 1 }
    $isCriticalOrHigh = ([string]$t.criticality -in @("critical", "high"))
    $isExpectedReady = ($expected -eq "Ready")
    $executionHealthy = $true
    if (-not $IgnoreExecutionHealth -and $snap.exists -and $isCriticalOrHigh -and $isExpectedReady) {
        # Task Scheduler can expose transient non-zero last_result (for example 267009)
        # while a task is actively running; treat Running as execution-healthy.
        if ($actual -eq "Running") {
            $executionHealthy = $true
        } else {
            $executionHealthy = Is-LastResultSuccess -value ([string]$snap.last_result)
        }
    }
    if ($skippedOptionalMissing) {
        $executionHealthy = $true
    }
    if (-not $executionHealthy) { $executionIssueCount += 1 }
    $items += [ordered]@{
        task_name = $name
        expected_status = $expected
        actual_status = $actual
        exists = $snap.exists
        drift = $drift
        enforce_action = $action
        enforce_ok = $enforcedOk
        owner = [string]$t.owner
        criticality = [string]$t.criticality
        optional = [bool]$optional
        skipped_optional_missing = [bool]$skippedOptionalMissing
        next_run_time = $snap.next_run_time
        last_result = $snap.last_result
        execution_healthy = $executionHealthy
    }
}

$criticalDrift = @($items | Where-Object { $_.drift -and $_.criticality -eq "critical" }).Count
$executionCriticalIssueCount = @($items | Where-Object { -not $_.execution_healthy -and $_.criticality -eq "critical" }).Count
$optionalSkippedMissingCount = @($items | Where-Object { $_.skipped_optional_missing }).Count
$allOk = ($driftCount -eq 0 -and $executionCriticalIssueCount -eq 0)

$payload = [ordered]@{
    schema = "automation_registry_reconcile_v1"
    ts_utc = [DateTimeOffset]::UtcNow.ToString("o")
    registry_path = $RegistryPath
    enforce = [bool]$Enforce
    all_ok = $allOk
    drift_count = $driftCount
    critical_drift_count = $criticalDrift
    optional_skipped_missing_count = $optionalSkippedMissingCount
    fixed_count = $fixedCount
    ignore_execution_health = [bool]$IgnoreExecutionHealth
    execution_issue_count = $executionIssueCount
    execution_critical_issue_count = $executionCriticalIssueCount
    items = $items
}

$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
$json = $payload | ConvertTo-Json -Depth 8
Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
if ($ShowJson) {
    Write-Host $json
}
Write-Host ("[reconcile] all_ok={0} drift_count={1} critical_drift={2} execution_issues={3} optional_missing_skipped={4} saved={5}" -f $allOk, $driftCount, $criticalDrift, $executionIssueCount, $optionalSkippedMissingCount, $OutputPath)

if (-not $allOk) { exit 1 }
exit 0
