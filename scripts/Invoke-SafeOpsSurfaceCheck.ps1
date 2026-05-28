<#
.SYNOPSIS
  단일 진입점: 로컬 운영 표면(태스크·JSON 신선도·RAM·추론 중복·선택 VPS 스모크)을 묶어 Fact-Lock 리포트를 남긴다.

.DESCRIPTION
  - Verify-TradingAutomationHealth.ps1 를 포함 실행한다.
  - 기본으로 `-AllowPolicyLockedGoNoGo`를 넘겨, `trading_go_no_go_latest.json`이 Trinity **LOCKED_MODE**로만 `NO_GO`인 경우(정책상 정상)를 **자동화 건강 실패로 취급하지 않는다**. 엄격히 보려면 `-StrictTradingGoNoGo`.
  - daemon_continuity / risk_profile / ops_phase1 의 타임스탬프 나이를 초과 시 기본은 warning(VPS 미러 전 로컬 표본 지연 허용). RAM 부족·추론 중복만 기본 critical.
  - run_mkm_control_integrity_inference_batch_v1 프로세스가 2개 이상이면 critical (RAM 폭주 재발 방지).
  - MCP 미주입·채팅 유무와 무관하게 동일 명령으로 재현 가능.

  - live_sync/incoming/daemon_alive_check.json 이 신선하면 daemon_continuity 경고를 생략한다 (Invoke-LiveSyncHeartbeatCheck.ps1).
  - -IgnoreLiveSync: 하트비트 검사·live_sync stale 경고·(로컬이 VPS 미러일 때의) daemon_continuity 지연 경고를 생략한다. Invoke-ProphecyLaneRecommendedClosureBundle -SkipLiveSyncPull 과 짝으로 쓴다.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-SafeOpsSurfaceCheck.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-SafeOpsSurfaceCheck.ps1 -IncludeVpsSmoke
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-SafeOpsSurfaceCheck.ps1 -StrictTradingGoNoGo
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [switch]$IncludeVpsSmoke,
    [switch]$StrictSecurity,
    [switch]$StrictDaemonCritical,
    [int]$DaemonWarnHours = 48,
    [int]$DaemonCriticalHours = 336,
    [int]$RiskWarnHours = 24,
    [int]$OpsPhase1WarnHours = 72,
    [double]$MinFreeRamGb = 1.5,
    [int]$LiveSyncMaxAgeSeconds = 600,
    [switch]$IgnoreLiveSync,
    # When false (default): pass -AllowPolicyLockedGoNoGo to Verify-TradingAutomationHealth so expected
    # Trinity LOCKED_MODE NO_GO does not fail the whole safe-ops tail (disk policy, not broken automation).
    [switch]$StrictTradingGoNoGo,
    # Optional strict mode: require MKM-Security-Integrity-Check-5min to be enabled.
    [switch]$StrictSecurityIntegrityTaskEnabled,
    # Forwarded to Verify-TradingAutomationHealth (Prophecy lane closure / local dev).
    [switch]$AllowDisabledSecurityIntegrityTask
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
Set-Location -LiteralPath $WorkspaceRoot

function Read-JsonFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try { return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json }
    catch { return $null }
}

function Get-AgeHours([string]$IsoDate) {
    if ([string]::IsNullOrWhiteSpace($IsoDate)) { return $null }
    try {
        $dto = [datetimeoffset]::Parse($IsoDate)
        return [math]::Round(([datetimeoffset]::UtcNow - $dto.ToUniversalTime()).TotalHours, 3)
    }
    catch { return $null }
}

$daemonPath = Join-Path $WorkspaceRoot "projects\bitcoin-trading\memory\v2\ops\daemon_continuity_latest.json"
$riskPath = Join-Path $WorkspaceRoot "projects\bitcoin-trading\memory\v2\risk\risk_profile_fact_safe_latest.json"
$opsPath = Join-Path $WorkspaceRoot "projects\bitcoin-trading\memory\v2\ops\ops_phase1_chain_report_latest.json"

$liveSyncFresh = $false
$heart = $null
if (-not $IgnoreLiveSync) {
    $hbScript = Join-Path $WorkspaceRoot "scripts\Invoke-LiveSyncHeartbeatCheck.ps1"
    if (Test-Path -LiteralPath $hbScript) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $hbScript -WorkspaceRoot $WorkspaceRoot -MaxAgeSeconds $LiveSyncMaxAgeSeconds | Out-Null
    }
    $heartPath = Join-Path $WorkspaceRoot "reports\live_sync_heartbeat_check_latest.json"
    $heart = Read-JsonFile -Path $heartPath
    if ($heart -and ($heart.fresh -eq $true)) {
        $liveSyncFresh = $true
    }
}

$daemon = Read-JsonFile -Path $daemonPath
$risk = Read-JsonFile -Path $riskPath
$ops = Read-JsonFile -Path $opsPath

$daemonAge = if ($daemon -and $daemon.ts) { Get-AgeHours "$($daemon.ts)" } elseif ($daemon -and $daemon.ts_utc) { Get-AgeHours "$($daemon.ts_utc)" } else { $null }
$riskAge = if ($risk -and $risk.generated_at) { Get-AgeHours "$($risk.generated_at)" } else { $null }
$opsAge = if ($ops -and $ops.ts_utc) { Get-AgeHours "$($ops.ts_utc)" } else { $null }

$staleness = [ordered]@{
    daemon_continuity_hours = $daemonAge
    daemon_warn_hours       = $DaemonWarnHours
    daemon_critical_hours   = $DaemonCriticalHours
    risk_profile_hours      = $riskAge
    risk_warn_hours         = $RiskWarnHours
    ops_phase1_hours        = $opsAge
    ops_phase1_warn_hours   = $OpsPhase1WarnHours
    live_sync_fresh         = $liveSyncFresh
    live_sync_max_age_sec   = $LiveSyncMaxAgeSeconds
}
if ($heart) {
    $staleness["live_sync_status"] = $heart.status
    $staleness["live_sync_age_seconds"] = $heart.age_seconds
}

$warnMsgs = [System.Collections.Generic.List[string]]::new()
$critMsgs = [System.Collections.Generic.List[string]]::new()

if (-not $IgnoreLiveSync -and $heart -and "$($heart.status)" -eq "stale") {
    $warnMsgs.Add("live_sync/incoming/daemon_alive_check.json stale (age > ${LiveSyncMaxAgeSeconds}s); refresh via VPS scp/cron")
}

if ($null -ne $daemonAge -and $StrictDaemonCritical -and ($daemonAge -gt $DaemonCriticalHours)) {
    $critMsgs.Add("daemon_continuity older than ${DaemonCriticalHours}h ($daemonAge h) [StrictDaemonCritical]")
}

if (-not $IgnoreLiveSync -and -not $liveSyncFresh) {
    if ($null -ne $daemonAge) {
        $daemonCrit = $StrictDaemonCritical -and ($daemonAge -gt $DaemonCriticalHours)
        if (-not $daemonCrit -and ($daemonAge -gt $DaemonWarnHours)) {
            $warnMsgs.Add("daemon_continuity stale (${daemonAge}h > ${DaemonWarnHours}h); local snapshot may lag VPS until live_sync")
        }
    }
    else {
        $warnMsgs.Add("daemon_continuity timestamp missing or unreadable")
    }
}

if ($null -ne $riskAge -and $riskAge -gt $RiskWarnHours) {
    $warnMsgs.Add("risk_profile_fact_safe older than ${RiskWarnHours}h ($riskAge h)")
}

if ($null -ne $opsAge -and $opsAge -gt $OpsPhase1WarnHours) {
    $warnMsgs.Add("ops_phase1_chain_report older than ${OpsPhase1WarnHours}h ($opsAge h)")
}

$os = Get-CimInstance Win32_OperatingSystem
$freeGb = [math]::Round($os.FreePhysicalMemory / 1024 / 1024, 2)
if ($freeGb -lt $MinFreeRamGb) {
    $critMsgs.Add("low_free_ram_gb=$freeGb threshold=$MinFreeRamGb")
}

$infCount = 0
$wmiPy = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*run_mkm_control_integrity_inference_batch_v1*' }
if ($wmiPy) { $infCount = @($wmiPy).Count }
if ($infCount -gt 1) {
    $critMsgs.Add("duplicate_inference_batch_processes count=$infCount (run Dedupe-MkmControlIntegrityInferenceBatch.ps1)")
}

$verifyScript = Join-Path $WorkspaceRoot "scripts\Verify-TradingAutomationHealth.ps1"
$verifyExit = -1
if (Test-Path -LiteralPath $verifyScript) {
    $verifyArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $verifyScript, "-WorkspaceRoot", $WorkspaceRoot)
    if (-not $StrictSecurity) {
        $verifyArgs += "-AllowExpectedSecurityDrift"
    }
    if (-not $StrictTradingGoNoGo) {
        $verifyArgs += "-AllowPolicyLockedGoNoGo"
    }
    if ($StrictSecurityIntegrityTaskEnabled) {
        $verifyArgs += "-StrictSecurityIntegrityTaskEnabled"
    }
    if ($AllowDisabledSecurityIntegrityTask) {
        $verifyArgs += "-AllowDisabledSecurityIntegrityTask"
    }
    & powershell.exe @verifyArgs
    $verifyExit = $LASTEXITCODE
}
else {
    $warnMsgs.Add("Verify-TradingAutomationHealth.ps1 missing")
}

$vpsSmoke = $null
if ($IncludeVpsSmoke) {
    $smokePs1 = Join-Path $WorkspaceRoot "scripts\Invoke-VpsOpsSmoke_v1.ps1"
    if (Test-Path -LiteralPath $smokePs1) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $smokePs1 -WorkspaceRoot $WorkspaceRoot -SoftFail
        $vpsSmoke = @{ last_exit_code = $LASTEXITCODE }
    }
}

$critical = $critMsgs.Count -gt 0
$warnings = $warnMsgs.Count -gt 0 -or $verifyExit -eq 1

# Critical is reserved for RAM / duplicate inference (recoverable ops incidents).
$overallSafe = ($verifyExit -eq 0) -and -not $critical -and -not $warnings
$status = if ($critical) { "critical" } elseif ($warnings -or $verifyExit -ne 0) { "degraded" } else { "ok" }

$report = [ordered]@{
    schema             = "safe_ops_surface_check_v1"
    generated_at_utc   = [datetime]::UtcNow.ToString("o")
    workspace_root     = $WorkspaceRoot
    status             = $status
    overall_safe       = $overallSafe
    free_ram_gb        = $freeGb
    min_free_ram_gb    = $MinFreeRamGb
    inference_batch_duplicate_count = $infCount
    verify_trading_automation_exit_code = $verifyExit
    staleness          = $staleness
    messages           = @{
        critical = @($critMsgs)
        warning  = @($warnMsgs)
    }
    artifacts          = @{
        trading_automation_health = (Join-Path $WorkspaceRoot "reports\trading_automation_health_latest.json")
        vps_ops_smoke             = if ($IncludeVpsSmoke) { (Join-Path $WorkspaceRoot "reports\vps_ops_smoke_latest.json") } else { $null }
    }
}

$outPath = Join-Path $WorkspaceRoot "reports\safe_ops_surface_check_latest.json"
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Output "safe_ops_surface_check_written=$outPath"
Write-Output "status=$status overall_safe=$overallSafe verify_exit=$verifyExit critical=$($critMsgs.Count) warnings=$($warnMsgs.Count)"

if ($critical) { exit 2 }
if ($warnings -or $verifyExit -ne 0) { exit 1 }
exit 0
