# Governed AI Customization — Cursor dogfood kickoff (baseline snapshot -> optional queue swap -> session upgrade chain)
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipQueueSwap,
    [switch]$SkipSessionUpgrade,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$steps = [ordered]@{}
$ok = $true

function Step {
    param([string]$Name, [scriptblock]$Block)
    if ($WhatIfOnly) {
        Write-Host "[WhatIf] step: $Name" -ForegroundColor DarkGray
        $steps[$Name] = @{ exit_code = 0; ok = $true; what_if = $true }
        return 0
    }
    & $Block
    $code = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
    $steps[$Name] = @{ exit_code = $code; ok = ($code -eq 0) }
    if ($code -ne 0) { $script:ok = $false }
    return $code
}

Write-Host "=== Cursor dogfood kickoff (Governed AI Customization) ===" -ForegroundColor Cyan
Write-Host "Rollback: scripts\Invoke-CursorDogfoodRollback_v1.ps1" -ForegroundColor Yellow

Step "safety_baseline" {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-CursorDogfoodSafetyBaseline_v1.ps1")
} | Out-Null
if (-not $ok) { exit 1 }

if (-not $SkipQueueSwap) {
    $src = Join-Path $WorkspaceRoot "docs\final\artifacts\todo_queue_cursor_dogfood_v1.json"
    $dst = Join-Path $WorkspaceRoot "docs\final\artifacts\todo_queue_latest.json"
    if (-not (Test-Path -LiteralPath $src)) {
        Write-Error "Missing: $src"
    }
    if ($WhatIfOnly) {
        Write-Host "[WhatIf] copy todo_queue_cursor_dogfood_v1.json -> todo_queue_latest.json"
    } else {
        Copy-Item -LiteralPath $src -Destination $dst -Force
        Write-Host "QUEUE_SWAPPED: todo_queue_cursor_dogfood_v1 -> todo_queue_latest.json"
    }
    $steps["queue_swap"] = @{ exit_code = 0; ok = $true }
}

if (-not $SkipSessionUpgrade) {
    Step "cursor_session_upgrade" {
        powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-MkmCursorSessionUpgrade_v1.ps1")
    } | Out-Null
}

Step "evolution_allowlist" {
    py (Join-Path $WorkspaceRoot "scripts\check_evolution_auto_apply_allowlist_v1.py")
} | Out-Null

Step "p0_paths" {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-MkmPersonaHealth_v1.ps1") -Persona P0
} | Out-Null

$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.ffffffZ")
$report = [ordered]@{
    schema           = "cursor_dogfood_kickoff_v1"
    generated_at_utc = $utc
    ok               = $ok
    steps            = $steps
    rollback_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CursorDogfoodRollback_v1.ps1"
    boundary_ack     = "[HYPO] Cursor dogfood B-track; Track A live SEND auto-merge forbidden"
}
$out = Join-Path $WorkspaceRoot "reports\cursor_dogfood_kickoff_v1_latest.json"
($report | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $out -Encoding UTF8
Write-Host "WROTE: $out"
Write-Host "CURSOR_DOGFOOD_KICKOFF_OK=$ok"
if (-not $ok) { exit 1 }
exit 0
