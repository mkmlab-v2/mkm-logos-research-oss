<#
.SYNOPSIS
  Apply MKM lean MCP profile to .cursor/mcp.json and verify readiness.

.DESCRIPTION
  SSOT: docs/final/artifacts/mcp_lean_profile_emergency_recovery_v1.json
  Removes openchrome + hostinger from mcp.json (lean 7 servers).
  Cursor Settings MCP toggles follow mcp.json after Developer: Reload Window.

.PARAMETER WhatIfOnly
  Report drift only; do not write mcp.json.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-McpLeanProfileAlign_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$WhatIfOnly,
    [switch]$SkipReadiness
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$mcpPath = Join-Path $WorkspaceRoot ".cursor\mcp.json"
$leanProfile = Join-Path $WorkspaceRoot ".cursor\mcp-profiles\lean.json"
$outJson = Join-Path $WorkspaceRoot "reports\mcp_lean_profile_align_latest.json"
$switchScript = Join-Path $WorkspaceRoot "scripts\Switch-McpProfile.ps1"

if (-not (Test-Path -LiteralPath $leanProfile)) {
    throw "Missing lean profile: $leanProfile"
}

function Get-ServerNames([string]$Path) {
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    return @($raw.mcpServers.PSObject.Properties.Name | Sort-Object)
}

$before = Get-ServerNames $mcpPath
$afterExpected = Get-ServerNames $leanProfile
$removed = @($before | Where-Object { $_ -notin $afterExpected })
$added = @($afterExpected | Where-Object { $_ -notin $before })
$forbidden = @("hostinger-website-manager", "playwright", "manseryeok-mcp")
$foundForbidden = @($before | Where-Object { $_ -in $forbidden })

$doc = [ordered]@{
    schema              = "mcp_lean_profile_align_v1"
    generated_at_utc    = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    mcp_path            = $mcpPath
    lean_profile        = $leanProfile
    servers_before      = $before
    servers_after_target = $afterExpected
    removed             = $removed
    added               = $added
    forbidden_found_before = $foundForbidden
    what_if_only        = [bool]$WhatIfOnly
    applied             = $false
    readiness           = $null
}

Write-Host "=== MCP lean profile align ===" -ForegroundColor Cyan
Write-Host "before : $($before -join ', ')"
Write-Host "target : $($afterExpected -join ', ')"
if ($removed.Count -gt 0) { Write-Host "remove : $($removed -join ', ')" -ForegroundColor Yellow }
if ($foundForbidden.Count -gt 0) { Write-Host "forbidden present: $($foundForbidden -join ', ')" -ForegroundColor Red }

$alreadyLean = ($removed.Count -eq 0 -and $added.Count -eq 0 -and $foundForbidden.Count -eq 0)
if ($alreadyLean) {
    Write-Host "Already lean — no mcp.json write needed." -ForegroundColor Green
    $doc.applied = $false
    $doc.note = "already_lean"
}
elseif ($WhatIfOnly) {
    Write-Host "WhatIfOnly: would apply lean profile." -ForegroundColor DarkGray
    $doc.note = "what_if_only"
}
else {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $switchScript -Profile lean
    if ($LASTEXITCODE -ne 0) { throw "Switch-McpProfile lean exit $LASTEXITCODE" }
    $doc.applied = $true
    $doc.note = "applied_lean"
    Write-Host "Applied lean profile -> $mcpPath" -ForegroundColor Green
}

if (-not $SkipReadiness) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\run_mkm_ai_v2_readiness_check.ps1")
    $readinessExit = $LASTEXITCODE
    $readinessPath = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_ai_v2_readiness_latest.json"
    if (Test-Path -LiteralPath $readinessPath) {
        $doc.readiness = Get-Content -LiteralPath $readinessPath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    if ($readinessExit -ne 0 -and -not $WhatIfOnly) {
        Write-Host "WARN: readiness exit $readinessExit (see mkm_ai_v2_readiness_latest.json)" -ForegroundColor Yellow
    }
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outJson, ($doc | ConvertTo-Json -Depth 8) + "`n", $utf8NoBom)
Write-Host "Report: $outJson" -ForegroundColor Cyan

if ($doc.applied -or (-not $alreadyLean -and -not $WhatIfOnly)) {
    Write-Host ""
    Write-Host "Next (required for Cursor Settings to match):" -ForegroundColor Yellow
    Write-Host "  1) Developer: Reload Window"
    Write-Host "  2) Settings -> MCP: confirm openchrome OFF / lean 7 servers only"
    Write-Host "  3) Start a NEW chat (tool catalog fixed at chat start)"
    Write-Host "  4) Browser smoke: Features -> Browser Automation ON (browser_* is NOT in mcp.json)"
    Write-Host ""
    Write-Host "OpenChrome on demand: scripts\Switch-McpProfile.ps1 -Profile with-openchrome" -ForegroundColor DarkGray
}

if ($WhatIfOnly) { exit 0 }
if ($doc.readiness -and $doc.readiness.overall_passed -eq $false -and $doc.applied) { exit 1 }
exit 0
