#Requires -Version 5.1
<#
.SYNOPSIS
  Lightweight browser view warmup — no Reload Window.

.DESCRIPTION
  Persists browser diet settings, opens Browser Tab via Cursor CLI, optional preview server.
  Run on session resume / logon when Cursor is already open.
  After warmup: start NEW Agent chat for browser_* injection (per-chat).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CursorIdeBrowserWarmup_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$Port = 8796,
    [switch]$SkipPreviewServer
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

. (Join-Path $PSScriptRoot "Cursor-IdeBrowserCommon_v1.ps1")

if (-not (Test-CursorProcessRunning)) {
    Write-Host "SKIP: Cursor.exe not running — warmup needs an open Cursor window" -ForegroundColor Yellow
    exit 3
}

$dietPy = Join-Path $WorkspaceRoot "scripts\apply_cursor_mcp_plugin_diet_auto_v1.py"
if (Test-Path -LiteralPath $dietPy) {
    & py $dietPy
    if ($LASTEXITCODE -ne 0) { throw "apply_cursor_mcp_plugin_diet_auto_v1.py exit $LASTEXITCODE" }
}

if (-not $SkipPreviewServer) {
    $smoke = Join-Path $WorkspaceRoot "scripts\Invoke-KoShortsCursorBrowserSmoke_v1.ps1"
    if (Test-Path -LiteralPath $smoke) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $smoke -Port $Port | Out-Null
    }
}

Write-Host "Opening Browser Tab (no reload)..." -ForegroundColor Yellow
Open-CursorIdeBrowserTab -WorkspaceRoot $WorkspaceRoot
Start-Sleep -Seconds 3

$check = Join-Path $WorkspaceRoot "scripts\check_cursor_ide_browser_readiness_v1.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $check -WorkspaceRoot $WorkspaceRoot
$exitCode = $LASTEXITCODE

$readiness = $null
$rp = Join-Path $WorkspaceRoot "reports\cursor_ide_browser_readiness_latest.json"
if (Test-Path -LiteralPath $rp) {
    $readiness = Get-Content -LiteralPath $rp -Raw | ConvertFrom-Json
}

$outJson = Join-Path $WorkspaceRoot "reports\cursor_ide_browser_warmup_latest.json"
$payload = [ordered]@{
    schema           = "cursor_ide_browser_warmup_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    readiness_exit   = $exitCode
    host_ready       = $(if ($readiness) { $readiness.host_ready_for_new_chat } else { $false })
    root_causes      = $(if ($readiness) { @($readiness.root_causes) } else { @() })
    preview_url      = "http://127.0.0.1:$Port/ko_shorts_cursor_preview_v1.html"
    next_step        = "NEW Agent chat -> browser_tabs (reload only if host_ready=false)"
    command          = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CursorIdeBrowserWarmup_v1.ps1"
}
$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outJson -Encoding UTF8

Write-Host "Warmup done. host_ready=$($payload.host_ready) exit=$exitCode" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Yellow" })
Write-Host "Report: $outJson"
exit $exitCode
