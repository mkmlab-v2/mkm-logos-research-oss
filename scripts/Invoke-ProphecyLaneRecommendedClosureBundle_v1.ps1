#Requires -Version 5.1
<#
.SYNOPSIS
  권장 순서로 예언·정렬·운영 표면을 한 번에 검증하고 일단락 리포트를 남긴다.

.DESCRIPTION
  Fact-Lock 권장안(스냅샷 P0–P1·Safe ops)에 맞춘 **운영 본선 일단락** 번들이다. 주문·실매매를 켜지 않으며,
  exit code와 `reports/prophecy_lane_closure_bundle_v1_latest.json`만으로 완료 여부를 판정한다.

  순서:
  1) verify_p0_constitution_gate_paths.ps1
  2) check_btrack_prophecy_chain_prereqs_v1.py (--stdout-only; -StrictPrereqs 시 --strict)
  3) run_prophecy_alignment_pytest.ps1 (bitcoin-trading 경로)
  4) (선택) Invoke-LiveSyncHeartbeatPull.ps1 -SoftFail — VPS 미설정 시 skipped여도 번들은 계속
  5) Invoke-SafeOpsSurfaceCheck.ps1 — verify_exit 0 기대; -SkipLiveSyncPull 이면 SafeOps에 -IgnoreLiveSync 전달(로컬 미러 지연으로 degraded 방지). -SkipSafeOpsSurfaceCheck 이면 5단계 전체 생략(로컬 go_no_go 경고만 우회할 때; 운영 본선 기본은 생략 금지 권장).
  6) build_trading_go_nogo_status_v1.py --exit-zero-on-no-go — 디스크 SSOT 갱신(판정은 JSON 참조)

.PARAMETER SkipLiveSyncPull
  4단계 live_sync 풀 생략.

.PARAMETER SkipGoNoGoRefresh
  6단계 GO/NO_GO JSON 재생성 생략.

.PARAMETER SkipSafeOpsSurfaceCheck
  5단계 `Invoke-SafeOpsSurfaceCheck.ps1` 생략(로컬에서 `go_no_go_ok=false` 등으로 verify_exit=1일 때 번들만 먼저 녹이고 싶을 때). 본선 관제 생략이므로 운영 승격 전에는 끄는 것이 기본이다.

.EXAMPLE
  Set-Location C:\workspace
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "",
    [switch]$StrictPrereqs,
    [switch]$SkipLiveSyncPull,
    [switch]$SkipGoNoGoRefresh,
    [switch]$SkipSafeOpsSurfaceCheck,
    [switch]$SkipWebhook
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
Set-Location -LiteralPath $WorkspaceRoot

$reportPath = Join-Path $WorkspaceRoot "reports\prophecy_lane_closure_bundle_v1_latest.json"
$steps = [System.Collections.Generic.List[object]]::new()
$ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$closureOk = $false
$failureMessage = $null

function Add-Step([string]$Name, $ExitCode) {
    $script:steps.Add([ordered]@{ name = $Name; exit_code = $ExitCode }) | Out-Null
}

# Use call operator with argument array
# Second parameter must not be named $Args (conflicts with PowerShell automatic variable).
function Invoke-BundleScript([string]$RelPath, [string[]]$ScriptArguments) {
    $full = Join-Path $WorkspaceRoot $RelPath
    if (-not (Test-Path -LiteralPath $full)) { throw "Missing script: $full" }
    $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $full) + $ScriptArguments
    $p = Start-Process -FilePath "powershell.exe" -ArgumentList $argList -WorkingDirectory $WorkspaceRoot `
        -Wait -PassThru -NoNewWindow
    return [int]$p.ExitCode
}

function Send-ClosureAlert([object]$ResultObject) {
    if ($SkipWebhook) { return }
    $webhook = $env:PROPHECY_LANE_CLOSURE_WEBHOOK_URL
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:OPS_ALARM_WEBHOOK_URL
    }
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        Write-Host "Webhook alert skipped: no PROPHECY_LANE_CLOSURE_WEBHOOK_URL or OPS_ALARM_WEBHOOK_URL" -ForegroundColor DarkGray
        return
    }
    $payload = [ordered]@{
        event = "prophecy_lane_closure_failed"
        ts_utc = (Get-Date).ToUniversalTime().ToString("o")
        workspace = $WorkspaceRoot
        closure_ok = $false
        closure = ($ResultObject | ConvertTo-Json -Depth 12 | ConvertFrom-Json)
    }
    $body = $payload | ConvertTo-Json -Depth 12 -Compress
    try {
        $null = Invoke-RestMethod -Uri $webhook -Method Post -Body $body -ContentType "application/json; charset=utf-8" -TimeoutSec 30
        Write-Host "Webhook alert sent: prophecy_lane_closure_failed" -ForegroundColor Yellow
    }
    catch {
        Write-Warning "Webhook alert failed: $($_.Exception.Message)"
    }
}

try {
    $e0 = Invoke-BundleScript "scripts\verify_p0_constitution_gate_paths.ps1" @()
    Add-Step "verify_p0" $e0
    if ($e0 -ne 0) { throw "verify_p0 failed exit $e0" }

    $prArgs = @("scripts\check_btrack_prophecy_chain_prereqs_v1.py", "--stdout-only")
    if ($StrictPrereqs) { $prArgs += "--strict" }
    & py @prArgs
    $e1 = $LASTEXITCODE
    Add-Step "check_btrack_prophecy_chain_prereqs" $e1
    if ($e1 -ne 0) { throw "check_btrack_prophecy_chain_prereqs failed exit $e1" }

    $e2 = Invoke-BundleScript "projects\bitcoin-trading\ops\v2\tasks\run_prophecy_alignment_pytest.ps1" @()
    Add-Step "run_prophecy_alignment_pytest" $e2
    if ($e2 -ne 0) { throw "run_prophecy_alignment_pytest failed exit $e2" }

    if (-not $SkipLiveSyncPull) {
        $e3 = Invoke-BundleScript "scripts\Invoke-LiveSyncHeartbeatPull.ps1" @("-SoftFail")
        Add-Step "Invoke_LiveSyncHeartbeatPull_SoftFail" $e3
        if ($e3 -ne 0) { throw "Invoke-LiveSyncHeartbeatPull failed exit $e3" }
    }
    else {
        Add-Step "Invoke_LiveSyncHeartbeatPull_SoftFail_skipped" $null
    }

    if (-not $SkipSafeOpsSurfaceCheck) {
        $safeOpsArgs = @()
        if ($SkipLiveSyncPull) {
            $safeOpsArgs += "-IgnoreLiveSync"
        }
        $e4 = Invoke-BundleScript "scripts\Invoke-SafeOpsSurfaceCheck.ps1" $safeOpsArgs
        Add-Step "Invoke_SafeOpsSurfaceCheck" $e4
        if ($e4 -ne 0) { throw "Invoke-SafeOpsSurfaceCheck failed exit $e4" }
    }
    else {
        Add-Step "Invoke_SafeOpsSurfaceCheck_skipped" $null
    }

    if (-not $SkipGoNoGoRefresh) {
        Push-Location $WorkspaceRoot
        try {
            & py "scripts\build_trading_go_nogo_status_v1.py" "--exit-zero-on-no-go"
            $e5 = $LASTEXITCODE
        }
        finally {
            Pop-Location
        }
        Add-Step "build_trading_go_nogo_status_v1" $e5
        if ($e5 -ne 0) { throw "build_trading_go_nogo_status_v1 failed exit $e5" }
    }
    else {
        Add-Step "build_trading_go_nogo_status_v1_skipped" $null
    }
    $closureOk = $true
}
catch {
    $closureOk = $false
    $failureMessage = $_.Exception.Message
    Write-Warning "prophecy lane closure failed: $failureMessage"
}

$safe = $null
if (Test-Path -LiteralPath (Join-Path $WorkspaceRoot "reports\safe_ops_surface_check_latest.json")) {
    try {
        $safe = Get-Content -LiteralPath (Join-Path $WorkspaceRoot "reports\safe_ops_surface_check_latest.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch { $safe = $null }
}

$out = [ordered]@{
    schema              = "prophecy_lane_closure_bundle_v1"
    generated_at_utc    = $ts
    workspace_root      = $WorkspaceRoot
    closure_ok          = $closureOk
    recommended_scope   = "ops_mainline_observability_only_no_orders"
    steps               = $steps
    safe_ops_status     = if ($safe) { $safe.status } else { $null }
    safe_ops_overall_safe = if ($safe) { $safe.overall_safe } else { $null }
    failure_message     = $failureMessage
    manual_remainder    = @(
        "GeneralProphecyDailyQueueV1 and GeneralProphecyHoldoutEvolutionWeeklyV1 (schtasks): configure logon+credentials in Task Scheduler if logoff execution is required."
        "Track A commercial promotion and live execution remain separate human-gated workflows per P0_COMMERCIALIZATION_TRACKER.md."
    )
    notes               = "Does not start live trading. Re-run weekly or after material config changes."
}

if (-not (Test-Path -LiteralPath (Split-Path -Parent $reportPath))) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $reportPath) -Force | Out-Null
}
$out | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "[DONE] Wrote $reportPath" -ForegroundColor Green
if (-not $closureOk) {
    Send-ClosureAlert -ResultObject $out
    exit 1
}
exit 0
