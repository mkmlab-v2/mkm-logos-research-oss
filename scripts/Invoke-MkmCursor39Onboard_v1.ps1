#Requires -Version 5.1
<#
.SYNOPSIS
  Cursor 3.9 onboard — Step1 MCP Customize · Step2 in-cloud env · Step3 pre-push /review.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmCursor39Onboard_v1.ps1
  powershell -File scripts\Invoke-MkmCursor39Onboard_v1.ps1 -Lane design -SkipCloudVerify
#>
param(
    [ValidateSet("", "oracle", "prophecy", "ops", "infra", "design", "web_ops", "ms")]
    [string]$Lane = "ops",
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipCloudVerify,
    [switch]$SkipBudgetGate,
    [switch]$WhatIf,
    [switch]$AutoLocalReview
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$report = [ordered]@{
    schema           = "mkm_cursor_39_onboard_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    lane             = $Lane
    steps            = @()
    exit_code        = 0
}
$outPath = Join-Path $WorkspaceRoot "reports\mkm_cursor_39_onboard_v1_latest.json"

function Add-Step {
    param([string]$Name, [int]$ExitCode, [string]$Detail = "")
    $report.steps += [ordered]@{
        step   = $Name
        exit   = $ExitCode
        detail = $Detail
    }
    if ($ExitCode -ne 0 -and $report.exit_code -eq 0) { $report.exit_code = $ExitCode }
}

Write-Host "=== Step 1/3: Customize MCP (default plugin OFF + lane coordinator) ===" -ForegroundColor Cyan
$syncPy = Join-Path $WorkspaceRoot "scripts\persist_cursor_mcp_disabled_servers_v1.py"
if ($WhatIf) {
    Add-Step "mcp_sync" 0 "what-if"
} else {
    & py $syncPy sync --apply
    Add-Step "mcp_sync" $LASTEXITCODE
    if ($LASTEXITCODE -ne 0) { throw "mcp sync exit $LASTEXITCODE" }
}

if (-not $SkipBudgetGate) {
    $budget = Join-Path $WorkspaceRoot "scripts\Invoke-McpPluginToolBudgetGate_v1.ps1"
    if (Test-Path -LiteralPath $budget) {
        if ($WhatIf) {
            Add-Step "budget_gate" 0 "what-if"
        } else {
            & $budget
            Add-Step "budget_gate" $LASTEXITCODE
        }
    }
}

$coord = Join-Path $WorkspaceRoot "scripts\Invoke-MkmMcpCoordinator_v1.ps1"
if ($Lane -and (Test-Path -LiteralPath $coord)) {
    if ($WhatIf) {
        Add-Step "mcp_coordinator" 0 "lane=$Lane what-if"
    } else {
        & $coord -Lane $Lane
        Add-Step "mcp_coordinator" $LASTEXITCODE "lane=$Lane"
    }
}

Write-Host "SSOT: docs/final/artifacts/mkm_cursor_customize_mcp_v39_latest.json" -ForegroundColor DarkGray
Write-Host "Reload Window after Step 1 if MCP list changed." -ForegroundColor Yellow

Write-Host ""
Write-Host "=== Step 2/3: in-cloud environment verify ===" -ForegroundColor Cyan
$cloudPy = Join-Path $WorkspaceRoot "scripts\verify_p0_constitution_gate_paths_cloud_v1.py"
if ($SkipCloudVerify) {
    Add-Step "cloud_verify" 0 "skipped"
} elseif ($WhatIf) {
    Add-Step "cloud_verify" 0 "what-if"
} else {
    & py $cloudPy
    Add-Step "cloud_verify" $LASTEXITCODE
    $pytest = & py -m pytest (Join-Path $WorkspaceRoot "tests\test_verify_p0_constitution_gate_paths_cloud_v1.py") -q 2>&1
    $pytestExit = $LASTEXITCODE
    Add-Step "cloud_pytest" $pytestExit ($pytest | Out-String).Trim()
}
Write-Host "SSOT: docs/final/artifacts/mkm_in_cloud_offload_matrix_v1_latest.json" -ForegroundColor DarkGray
Write-Host "Cloud agents: /in-cloud  ·  PR loop: /babysit  ·  env: .cursor/environment.json" -ForegroundColor DarkGray

Write-Host ""
Write-Host "=== Step 3/3: pre-push /review habit ===" -ForegroundColor Cyan
$review = Join-Path $WorkspaceRoot "scripts\Invoke-CursorPrePushReview_v1.ps1"
if ($WhatIf) {
    Add-Step "pre_push_review" 0 "what-if"
} elseif ($AutoLocalReview) {
    & $review -AutoLocal
    Add-Step "pre_push_review" $LASTEXITCODE "auto_local"
} else {
    & $review -CheckOnly
    $reviewExit = $LASTEXITCODE
    Add-Step "pre_push_review" $reviewExit $(if ($reviewExit -eq 0) { "ack_ok" } else { "ack_missing_run_/review_then_-Ack" })
}

$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host ""
Write-Host "Wrote: $outPath" -ForegroundColor DarkGray

if ($report.exit_code -ne 0) {
    Write-Host "[PARTIAL] Steps 1-2 may be OK; Step 3 needs /review in chat then -Ack." -ForegroundColor Yellow
    exit $report.exit_code
}

Write-Host "[DONE] Cursor 3.9 onboard steps 1-3 complete." -ForegroundColor Green
exit 0
