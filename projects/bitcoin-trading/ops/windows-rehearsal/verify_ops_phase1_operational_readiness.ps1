param(
    [string]$TaskName = "\Bitcoin-Ops-Phase1-Chain-Daily",
    [string]$ReportPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_phase1_chain_report_latest.json",
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_phase1_readiness_latest.json",
    [int]$MaxReportAgeHours = 30,
    [switch]$Strict,
    [switch]$AllowNonZeroLastResult,
    [switch]$RequireBitcoinTradingOtelSmoke
)

$ErrorActionPreference = "Stop"

function Get-EnvAny([string]$name) {
    foreach ($scope in @("Process", "User", "Machine")) {
        $v = [Environment]::GetEnvironmentVariable($name, $scope)
        if (-not [string]::IsNullOrWhiteSpace($v)) { return $v }
    }
    return $null
}

function Is-LastResultSuccess([string]$value) {
    if ([string]::IsNullOrWhiteSpace($value)) { return $false }
    $v = $value.Trim().ToLowerInvariant()
    if ($v -eq "0") { return $true }
    if ($v -eq "0x0") { return $true }
    if ($v -eq "the operation completed successfully. (0x0)") { return $true }
    return $false
}

$checks = @()
$fail = $false
$lastResultGateOk = $true

schtasks /Query /TN $TaskName > $null 2>&1
$taskExists = ($LASTEXITCODE -eq 0)
if (-not $taskExists) {
    $checks += [ordered]@{ id = "task_exists"; ok = $false; detail = "schtasks_query_failed" }
    $fail = $true
}
else {
    $checks += [ordered]@{ id = "task_exists"; ok = $true; detail = $TaskName }
    $raw = schtasks /Query /TN $TaskName /V /FO LIST 2>$null
    $trLine = ($raw | Select-String "^Task To Run:\s+" | Select-Object -First 1)
    $logonLine = ($raw | Select-String "^Logon Mode:\s+" | Select-Object -First 1)
    $lastRun = ($raw | Select-String "^Last Run Time:\s+" | Select-Object -First 1)
    $lastRes = ($raw | Select-String "^Last Result:\s+" | Select-Object -First 1)
    $tr = if ($trLine) { ($trLine.ToString() -replace "^Task To Run:\s+", "").Trim() } else { "" }
    $logon = if ($logonLine) { ($logonLine.ToString() -replace "^Logon Mode:\s+", "").Trim() } else { "" }
    $checks += [ordered]@{
        id     = "task_to_run"
        ok     = ($tr -match "IncludeConstitutionGates")
        detail = if ($tr.Length -gt 220) { $tr.Substring(0, 220) + "..." } else { $tr }
    }
    if (-not ($tr -match "IncludeConstitutionGates")) { $fail = $true }
    $strictInTask = ($tr -match "(^|\s)-Strict(\s|$)")
    $checks += [ordered]@{
        id = "task_strict_mode_enabled"
        ok = $strictInTask
        detail = if ($strictInTask) { "strict_flag_present" } else { "strict_flag_missing" }
    }
    if (-not $strictInTask) { $fail = $true }
    $otelSmokeInTask = ($tr -match "(^|\s)-IncludeBitcoinTradingOtelSmoke(\s|$)")
    $checks += [ordered]@{
        id = "task_otel_smoke_enabled"
        ok = if ($RequireBitcoinTradingOtelSmoke) { $otelSmokeInTask } else { $true }
        detail = if ($otelSmokeInTask) { "otel_smoke_flag_present" } elseif ($RequireBitcoinTradingOtelSmoke) { "otel_smoke_flag_missing_required" } else { "otel_smoke_flag_missing_optional" }
    }
    if ($RequireBitcoinTradingOtelSmoke -and -not $otelSmokeInTask) { $fail = $true }
    $checks += [ordered]@{ id = "logon_mode"; ok = $true; detail = $logon; note = "Interactive only = may not run when logged off; set Run whether user is logged on if unattended required." }
    $checks += [ordered]@{
        id     = "last_run_time"
        ok     = $true
        detail = if ($lastRun) { ($lastRun.ToString() -replace "^Last Run Time:\s+", "").Trim() } else { "" }
    }
    $checks += [ordered]@{
        id     = "last_result"
        ok     = $true
        detail = if ($lastRes) { ($lastRes.ToString() -replace "^Last Result:\s+", "").Trim() } else { "" }
    }
    $lastResultValue = if ($lastRes) { ($lastRes.ToString() -replace "^Last Result:\s+", "").Trim() } else { "" }
    $lastResultOk = (Is-LastResultSuccess -value $lastResultValue) -or [bool]$AllowNonZeroLastResult
    $lastResultGateOk = $lastResultOk
    $checks += [ordered]@{
        id = "last_result_gate"
        ok = $lastResultOk
        detail = if ($AllowNonZeroLastResult) { "bypassed_allow_nonzero_last_result" } else { $lastResultValue }
    }
}

$alarmUrl = Get-EnvAny "OPS_ALARM_WEBHOOK_URL"
$checks += [ordered]@{
    id     = "ops_alarm_webhook_url"
    ok     = (-not [string]::IsNullOrWhiteSpace($alarmUrl))
    detail = if ([string]::IsNullOrWhiteSpace($alarmUrl)) { "missing" } else { "set" }
}
if ([string]::IsNullOrWhiteSpace($alarmUrl)) {
    if ($Strict) { $fail = $true }
}

$reportOk = $false
$reportAge = $null
$phase1ChainOverallOk = $false
$phase1Fresh = $false
if (Test-Path -LiteralPath $ReportPath) {
    try {
        $rep = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $ts = [DateTimeOffset]::Parse([string]$rep.ts_utc)
        $reportAge = [Math]::Round(([DateTimeOffset]::UtcNow - $ts).TotalHours, 2)
        $fresh = ($reportAge -le $MaxReportAgeHours)
        $phase1Fresh = $fresh
        $reportOk = $true
        if ($rep.PSObject.Properties.Name -contains "overall_chain_ok") {
            $phase1ChainOverallOk = [bool]$rep.overall_chain_ok
        }
        $checks += [ordered]@{ id = "phase1_report_fresh"; ok = $fresh; detail = "age_hours=$reportAge max=$MaxReportAgeHours" }
        if (-not $fresh -and $Strict) { $fail = $true }
    }
    catch {
        $checks += [ordered]@{ id = "phase1_report_fresh"; ok = $false; detail = "parse_error" }
        if ($Strict) { $fail = $true }
    }
}
else {
    $checks += [ordered]@{ id = "phase1_report_fresh"; ok = $false; detail = "file_missing" }
    if ($Strict) { $fail = $true }
}

if (-not $lastResultGateOk) {
    if ($phase1Fresh -and $phase1ChainOverallOk) {
        $checks += [ordered]@{
            id = "last_result_gate_override"
            ok = $true
            detail = "phase1_report_overrides_nonzero_last_result"
        }
    } else {
        $fail = $true
    }
}

$payload = [ordered]@{
    schema  = "ops_phase1_readiness_v1"
    ts_utc  = [DateTimeOffset]::UtcNow.ToString("o")
    runner  = "verify_ops_phase1_operational_readiness.ps1"
    strict  = [bool]$Strict
    all_ok  = (-not $fail)
    checks  = $checks
}

$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
$payload | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Host ("[readiness] WROTE {0} all_ok={1}" -f $OutputPath, (-not $fail))

if ($fail) {
    Write-Host "[readiness] FAIL (use -Strict only if you require alarm URL + fresh report)" -ForegroundColor Red
    exit 1
}
exit 0
