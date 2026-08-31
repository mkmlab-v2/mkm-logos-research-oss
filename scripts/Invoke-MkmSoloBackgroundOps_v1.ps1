param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$steps = [ordered]@{}
$ok = $true

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Block
    )
    & $Block
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    $steps[$Name] = @{ exit_code = $code }
    if ($code -ne 0) { $script:ok = $false }
    return $code
}

Invoke-Step "p0_constitution_paths" {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\verify_p0_constitution_gate_paths.ps1")
} | Out-Null

Invoke-Step "aiv2_readiness_check" {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\run_mkm_ai_v2_readiness_check.ps1") -WorkspaceRoot $WorkspaceRoot
} | Out-Null

Invoke-Step "scheduler_solo_core_stack_band" {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-MkmSchedulerSoloCoreStackAudit_v1.ps1") -WorkspaceRoot $WorkspaceRoot -EnforceSoloBand
} | Out-Null

# MCP coordinator (lane preset + persist sync) before budget/hygiene — non-fatal.
$mcpCoordScript = Join-Path $WorkspaceRoot "scripts\Invoke-MkmMcpCoordinator_v1.ps1"
if (Test-Path -LiteralPath $mcpCoordScript) {
    $coordOutLog = Join-Path $env:TEMP ("mkm_solo_ops_mcp_coord_out_{0}.log" -f $PID)
    $coordErrLog = Join-Path $env:TEMP ("mkm_solo_ops_mcp_coord_err_{0}.log" -f $PID)
    $coordProc = Start-Process -FilePath "powershell.exe" `
        -ArgumentList @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $mcpCoordScript,
            "-WorkspaceRoot", $WorkspaceRoot, "-SkipBudgetGate", "-SkipPluginDiet", "-SkipBrowserAutoFix"
        ) `
        -Wait -PassThru -NoNewWindow `
        -RedirectStandardOutput $coordOutLog `
        -RedirectStandardError $coordErrLog
    $coordCode = if ($null -eq $coordProc.ExitCode) { 0 } else { [int]$coordProc.ExitCode }
    Remove-Item -LiteralPath $coordOutLog, $coordErrLog -Force -ErrorAction SilentlyContinue
    $steps["mcp_coordinator"] = @{ exit_code = $coordCode; non_fatal = $true }
    if ($coordCode -ne 0) {
        Write-Warning "mcp_coordinator exit $coordCode (solo_ops core steps unchanged)"
    }
}

# MCP gate before hygiene: hygiene reads mcp_plugin_tool_budget_gate_latest.json (must be fresh).
$mcpBudgetScript = Join-Path $WorkspaceRoot "scripts\Invoke-McpPluginToolBudgetGate_v1.ps1"
if (Test-Path -LiteralPath $mcpBudgetScript) {
    $mcpOutLog = Join-Path $env:TEMP ("mkm_solo_ops_mcp_budget_out_{0}.log" -f $PID)
    $mcpErrLog = Join-Path $env:TEMP ("mkm_solo_ops_mcp_budget_err_{0}.log" -f $PID)
    $mcpProc = Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $mcpBudgetScript, "-WorkspaceRoot", $WorkspaceRoot) `
        -Wait -PassThru -NoNewWindow `
        -RedirectStandardOutput $mcpOutLog `
        -RedirectStandardError $mcpErrLog
    $mcpCode = if ($null -eq $mcpProc.ExitCode) { 0 } else { [int]$mcpProc.ExitCode }
    Remove-Item -LiteralPath $mcpOutLog, $mcpErrLog -Force -ErrorAction SilentlyContinue
    $steps["mcp_plugin_tool_budget_gate"] = @{ exit_code = $mcpCode; non_fatal = $true }
    if ($mcpCode -ne 0) {
        Write-Warning "mcp_plugin_tool_budget_gate exit $mcpCode (plugin MCP bloat — remediated if possible)"
    }
}

$hostHygieneScript = Join-Path $WorkspaceRoot "scripts\check_cursor_state_vscdb_hygiene_v1.ps1"
if (Test-Path -LiteralPath $hostHygieneScript) {
    Invoke-Step "cursor_host_vscdb_hygiene" {
        powershell -NoProfile -ExecutionPolicy Bypass -File $hostHygieneScript -WorkspaceRoot $WorkspaceRoot
    } | Out-Null
}

$hostJanitorScript = Join-Path $WorkspaceRoot "scripts\Invoke-CursorStateVscdbJanitor_v1.ps1"
if (Test-Path -LiteralPath $hostJanitorScript) {
    $janitorOutLog = Join-Path $env:TEMP ("mkm_solo_ops_cursor_janitor_out_{0}.log" -f $PID)
    $janitorErrLog = Join-Path $env:TEMP ("mkm_solo_ops_cursor_janitor_err_{0}.log" -f $PID)
    $janitorProc = Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $hostJanitorScript, "-WorkspaceRoot", $WorkspaceRoot, "-Apply") `
        -Wait -PassThru -NoNewWindow `
        -RedirectStandardOutput $janitorOutLog `
        -RedirectStandardError $janitorErrLog
    $janitorCode = if ($null -eq $janitorProc.ExitCode) { 0 } else { [int]$janitorProc.ExitCode }
    Remove-Item -LiteralPath $janitorOutLog, $janitorErrLog -Force -ErrorAction SilentlyContinue
    $steps["cursor_state_vscdb_janitor"] = @{ exit_code = $janitorCode; non_fatal = $true }
    if ($janitorCode -eq 2) {
        Write-Warning "cursor_state_vscdb_janitor skipped (Cursor running)"
    } elseif ($janitorCode -ne 0) {
        Write-Warning "cursor_state_vscdb_janitor exit $janitorCode"
    }
}

$perfScript = Join-Path $WorkspaceRoot "scripts\check_cursor_perf_snapshot.ps1"
if (Test-Path -LiteralPath $perfScript) {
    $perfOutLog = Join-Path $env:TEMP ("mkm_solo_ops_cursor_perf_out_{0}.log" -f $PID)
    $perfErrLog = Join-Path $env:TEMP ("mkm_solo_ops_cursor_perf_err_{0}.log" -f $PID)
    $perfProc = Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $perfScript) `
        -Wait -PassThru -NoNewWindow `
        -RedirectStandardOutput $perfOutLog `
        -RedirectStandardError $perfErrLog
    $perfCode = if ($null -eq $perfProc.ExitCode) { 0 } else { [int]$perfProc.ExitCode }
    Remove-Item -LiteralPath $perfOutLog, $perfErrLog -Force -ErrorAction SilentlyContinue
    $steps["cursor_perf_snapshot"] = @{ exit_code = $perfCode; non_fatal = $true }
    if ($perfCode -ne 0) {
        Write-Warning "cursor_perf_snapshot exit $perfCode (solo_ops core steps unchanged)"
    }
}

$dietScript = Join-Path $WorkspaceRoot "scripts\check_cursor_rules_context_diet_v1.py"
if (Test-Path -LiteralPath $dietScript) {
    $dietProc = Start-Process -FilePath "py" `
        -ArgumentList @($dietScript, "--strict") `
        -WorkingDirectory $WorkspaceRoot `
        -Wait -PassThru -NoNewWindow
    $dietCode = if ($null -eq $dietProc.ExitCode) { 0 } else { [int]$dietProc.ExitCode }
    $steps["cursor_rules_context_diet_strict"] = @{ exit_code = $dietCode; non_fatal = $true }
    if ($dietCode -ne 0) {
        Write-Warning "cursor_rules_context_diet_strict exit $dietCode (solo_ops core steps unchanged)"
    }
}

$nlRepairScript = Join-Path $WorkspaceRoot "scripts\Invoke-NotebookLmMcpAuthAutoRepair_v1.ps1"
if (Test-Path -LiteralPath $nlRepairScript) {
    # Child MCP/nlm logs on stderr must not terminate solo_ops (ErrorAction Stop + NativeCommandError).
    $nlOutLog = Join-Path $env:TEMP ("mkm_solo_ops_nl_repair_out_{0}.log" -f $PID)
    $nlErrLog = Join-Path $env:TEMP ("mkm_solo_ops_nl_repair_err_{0}.log" -f $PID)
    $nlProc = Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $nlRepairScript) `
        -Wait -PassThru -NoNewWindow `
        -RedirectStandardOutput $nlOutLog `
        -RedirectStandardError $nlErrLog
    $nlCode = if ($null -eq $nlProc.ExitCode) { 0 } else { [int]$nlProc.ExitCode }
    Remove-Item -LiteralPath $nlOutLog, $nlErrLog -Force -ErrorAction SilentlyContinue
    $steps["nl_mcp_auth_auto_repair"] = @{ exit_code = $nlCode; non_fatal = $true }
    if ($nlCode -ne 0) {
        Write-Warning "nl_mcp_auth_auto_repair exit $nlCode (solo_ops core steps unchanged)"
    }
}

$injectAlertPy = Join-Path $WorkspaceRoot "scripts\inject_cursor_host_alert_resume_pack_v1.py"
$degradedPath = Join-Path $WorkspaceRoot "reports\cursor_perf_degraded.json"
if ((Test-Path -LiteralPath $degradedPath) -and (Test-Path -LiteralPath $injectAlertPy)) {
    $injectProc = Start-Process -FilePath "py" `
        -ArgumentList @($injectAlertPy) `
        -WorkingDirectory $WorkspaceRoot `
        -Wait -PassThru -NoNewWindow
    $injectCode = if ($null -eq $injectProc.ExitCode) { 0 } else { [int]$injectProc.ExitCode }
    $steps["cursor_host_alert_resume_pack"] = @{ exit_code = $injectCode; non_fatal = $true }
    if ($injectCode -ne 0) {
        Write-Warning "cursor_host_alert_resume_pack exit $injectCode"
    }
}

# P1 wire: ops dynamical timeseries append when disk SSOT fingerprint changes (non-fatal).
$opsSnapScript = Join-Path $WorkspaceRoot "scripts\run_ops_dynamical_ops_snapshot_chain_v1.py"
if (Test-Path -LiteralPath $opsSnapScript) {
    & py $opsSnapScript
    $opsSnapCode = $LASTEXITCODE
    if ($null -eq $opsSnapCode) { $opsSnapCode = 0 }
    $steps["ops_dynamical_ops_snapshot"] = @{ exit_code = $opsSnapCode; non_fatal = $true }
    if ($opsSnapCode -ne 0) {
        Write-Warning "ops_dynamical_ops_snapshot exit $opsSnapCode (solo_ops core unchanged)"
    }
}

$utcNow = (Get-Date).ToUniversalTime()
$localDate = (Get-Date).ToString("yyyy-MM-dd")

$latest = [ordered]@{
    schema = "mkm_solo_background_ops_v1"
    generated_at_utc = $utcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")
    last_run_local_date = $localDate
    ok = $ok
    steps = $steps
    operator_note_ko = "Invoke-MkmSoloBackgroundOps_v1 — P0 + AIV2 + scheduler band + mcp_coordinator (non-fatal) + MCP budget + cursor hygiene + janitor + NL repair + resume-pack alert"
}

$state = [ordered]@{
    last_run_local_date = $localDate
    last_ok = $ok
    last_run_utc = $utcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")
}

$reportDir = Join-Path $WorkspaceRoot "reports"
if (-not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}

$latestPath = Join-Path $reportDir "mkm_solo_background_ops_latest.json"
$statePath = Join-Path $reportDir "mkm_solo_background_ops_state.json"
($latest | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $latestPath -Encoding UTF8
($state | ConvertTo-Json -Depth 4) | Set-Content -LiteralPath $statePath -Encoding UTF8

Write-Host "WROTE: $latestPath"
Write-Host "WROTE: $statePath"
Write-Host "SOLO_OPS_OK=$ok"

if (-not $ok) { exit 1 }
exit 0
