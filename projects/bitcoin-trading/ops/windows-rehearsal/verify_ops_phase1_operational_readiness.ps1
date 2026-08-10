param(
    [string]$TaskName = "\Bitcoin-Ops-Phase1-Chain-Daily",
    [string]$ReportPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_phase1_chain_report_latest.json",
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_phase1_readiness_latest.json",
    [string]$SignalBiasPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\signal_bias_snapshot_latest.json",
    [int]$MaxReportAgeHours = 30,
    [switch]$RequireConstitutionGates = $true,
    [switch]$RequireStrictMode = $true,
    [switch]$Strict,
    [switch]$AllowNonZeroLastResult,
    [switch]$RequireBitcoinTradingOtelSmoke,
    [double]$SignalBiasSellRatioWarn = 0.80,
    [double]$SignalBiasSellRatioFail = 0.95,
    [switch]$EnforceSignalBiasGuard
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

function Get-SchtasksFieldValue {
    param(
        [string[]]$Lines,
        [string[]]$Labels
    )
    foreach ($line in $Lines) {
        foreach ($label in $Labels) {
            $pattern = "^\s*" + [regex]::Escape($label) + "\s*:\s*(.+)$"
            $m = [regex]::Match($line, $pattern)
            if ($m.Success) {
                return $m.Groups[1].Value.Trim()
            }
        }
    }
    return ""
}

$checks = @()
$fail = $false
$lastResultGateOk = $true
$otelSmokeInTask = $null

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Query /TN $TaskName > $null 2>&1
$ErrorActionPreference = $oldEap
$taskExists = ($LASTEXITCODE -eq 0)
if (-not $taskExists) {
    $checks += [ordered]@{ id = "task_exists"; ok = $false; detail = "schtasks_query_failed" }
    $fail = $true
}
else {
    $checks += [ordered]@{ id = "task_exists"; ok = $true; detail = $TaskName }
    $raw = @(schtasks /Query /TN $TaskName /V /FO LIST 2>$null)
    $tr = Get-SchtasksFieldValue -Lines $raw -Labels @("Task To Run", "작업 실행")
    $logon = Get-SchtasksFieldValue -Lines $raw -Labels @("Logon Mode", "로그온 모드")
    $lastRunValue = Get-SchtasksFieldValue -Lines $raw -Labels @("Last Run Time", "마지막 실행 시간")
    $lastResultValue = Get-SchtasksFieldValue -Lines $raw -Labels @("Last Result", "마지막 결과")
    # schtasks /V LIST wraps long "Task To Run" on narrow/redirected consoles (Task Scheduler session).
    # Prefer Get-ScheduledTask action string when schtasks field looks truncated or missing flags.
    $trLooksTruncated = [string]::IsNullOrWhiteSpace($tr) -or
        ($tr -notmatch "IncludeConstitutionGates") -or
        ($tr -notmatch "(^|\s)-Strict(\s|$)")
    if ($trLooksTruncated) {
        try {
            $tn = $TaskName.TrimStart('\')
            $st = Get-ScheduledTask -TaskName $tn -ErrorAction Stop
            $parts = @()
            foreach ($a in @($st.Actions)) {
                $exe = [string]$a.Execute
                $arg = [string]$a.Arguments
                if (-not [string]::IsNullOrWhiteSpace($exe) -or -not [string]::IsNullOrWhiteSpace($arg)) {
                    $parts += (($exe + " " + $arg).Trim())
                }
            }
            $trCmd = ($parts -join " ").Trim()
            if (-not [string]::IsNullOrWhiteSpace($trCmd)) {
                $tr = $trCmd
            }
            if ([string]::IsNullOrWhiteSpace($logon) -and $st.Principal) {
                $logon = [string]$st.Principal.LogonType
            }
            $info = Get-ScheduledTaskInfo -TaskName $tn -ErrorAction SilentlyContinue
            if ($null -ne $info) {
                if ([string]::IsNullOrWhiteSpace($lastRunValue) -and $info.LastRunTime) {
                    $lastRunValue = $info.LastRunTime.ToString()
                }
                if ([string]::IsNullOrWhiteSpace($lastResultValue)) {
                    $lastResultValue = [string]$info.LastTaskResult
                }
            }
        } catch { }
    }
    $checks += [ordered]@{
        id     = "task_to_run"
        ok     = if ($RequireConstitutionGates) { ($tr -match "IncludeConstitutionGates") } else { $true }
        detail = if ($tr.Length -gt 220) { $tr.Substring(0, 220) + "..." } else { $tr }
    }
    $checks += [ordered]@{
        id     = "task_to_run_full"
        ok     = $true
        detail = $tr
    }
    if ($RequireConstitutionGates -and -not ($tr -match "IncludeConstitutionGates")) { $fail = $true }
    $strictInTask = ($tr -match "(^|\s)-Strict(\s|$)")
    $checks += [ordered]@{
        id = "task_strict_mode_enabled"
        ok = if ($RequireStrictMode) { $strictInTask } else { $true }
        detail = if ($strictInTask) { "strict_flag_present" } elseif ($RequireStrictMode) { "strict_flag_missing_required" } else { "strict_flag_missing_optional" }
    }
    if ($RequireStrictMode -and -not $strictInTask) { $fail = $true }
    # schtasks /V output can truncate long "Task To Run" strings, so allow prefix match.
    $otelSmokeInTask = ($tr -match "IncludeBitcoinTradingOtelSmo")
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
        detail = $lastRunValue
    }
    $checks += [ordered]@{
        id     = "last_result"
        ok     = $true
        detail = $lastResultValue
    }
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

$signalBiasGuardFail = $false
if (Test-Path -LiteralPath $SignalBiasPath) {
    try {
        $bias = Get-Content -LiteralPath $SignalBiasPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $sellRatio = 0.0
        $windowCount = 0
        if ($bias.PSObject.Properties.Name -contains "ratios" -and $bias.ratios) {
            $sellRatio = [double]$bias.ratios.sell_ratio
        }
        if ($bias.PSObject.Properties.Name -contains "signal_count_window") {
            $windowCount = [int]$bias.signal_count_window
        }
        $guardLevel = "ok"
        if ($sellRatio -ge $SignalBiasSellRatioFail) {
            $guardLevel = "fail"
            $signalBiasGuardFail = $true
        }
        elseif ($sellRatio -ge $SignalBiasSellRatioWarn) {
            $guardLevel = "warn"
        }
        $checks += [ordered]@{
            id = "signal_bias_guard"
            ok = if ($EnforceSignalBiasGuard) { -not $signalBiasGuardFail } else { $true }
            detail = ("sell_ratio={0} window_count={1} warn={2} fail={3} level={4}" -f `
                ([Math]::Round($sellRatio, 4)), $windowCount, $SignalBiasSellRatioWarn, $SignalBiasSellRatioFail, $guardLevel)
        }
        if ($EnforceSignalBiasGuard -and $signalBiasGuardFail) { $fail = $true }
    }
    catch {
        $checks += [ordered]@{
            id = "signal_bias_guard"
            ok = $false
            detail = "parse_error"
        }
        if ($EnforceSignalBiasGuard) { $fail = $true }
    }
}
else {
    $checks += [ordered]@{
        id = "signal_bias_guard"
        ok = if ($EnforceSignalBiasGuard) { $false } else { $true }
        detail = "file_missing"
    }
    if ($EnforceSignalBiasGuard) { $fail = $true }
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
        if ($rep.PSObject.Properties.Name -contains "include_bitcoin_trading_otel_smoke") {
            $otelSmokeInReport = [bool]$rep.include_bitcoin_trading_otel_smoke
            $checks += [ordered]@{
                id = "phase1_report_otel_smoke_included"
                ok = if ($RequireBitcoinTradingOtelSmoke) { $otelSmokeInReport } else { $true }
                detail = if ($otelSmokeInReport) { "otel_smoke_included" } elseif ($RequireBitcoinTradingOtelSmoke) { "otel_smoke_not_included_required" } else { "otel_smoke_not_included_optional" }
            }
            if ($RequireBitcoinTradingOtelSmoke -and -not $otelSmokeInReport) { $fail = $true }
            if ($null -ne $otelSmokeInTask) {
                $otelCrossOk = ($otelSmokeInTask -eq $otelSmokeInReport)
                $checks += [ordered]@{
                    id = "otel_smoke_task_report_consistency"
                    ok = if ($RequireBitcoinTradingOtelSmoke) { $otelCrossOk } else { $true }
                    detail = if ($otelCrossOk) { "task_and_report_match" } elseif ($RequireBitcoinTradingOtelSmoke) { "task_report_mismatch_required" } else { "task_report_mismatch_optional" }
                }
                if ($RequireBitcoinTradingOtelSmoke -and -not $otelCrossOk) { $fail = $true }
            }
        } else {
            $checks += [ordered]@{
                id = "phase1_report_otel_smoke_included"
                ok = if ($RequireBitcoinTradingOtelSmoke) { $false } else { $true }
                detail = if ($RequireBitcoinTradingOtelSmoke) { "field_missing_required" } else { "field_missing_optional" }
            }
            if ($RequireBitcoinTradingOtelSmoke) { $fail = $true }
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
