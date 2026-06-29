#Requires -Version 5.1
<#
.SYNOPSIS
  Copy Cursor Automation agent instructions to clipboard (UI paste helper).

.PARAMETER AutomationId
  weekly_doc_sync | weekly_test_recovery | daily_patrol_failure_triage | internal_pr_review
  Or raw cursor UUID (e.g. c8aa5b5e-527e-4a3f-8e6d-ce1d155dde36).

.PARAMETER OpenEditUrl
  Open cursor.com automation edit page in default browser.

.EXAMPLE
  powershell -File scripts\Invoke-CopyMkmCursorAutomationPaste_v1.ps1 -AutomationId weekly_doc_sync -OpenEditUrl
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$AutomationId,

    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$OpenEditUrl
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $WorkspaceRoot

$pastePath = Join-Path $WorkspaceRoot 'docs\final\artifacts\mkm_cursor_automation_ui_paste_v1.json'
if (-not (Test-Path -LiteralPath $pastePath)) {
    throw "Missing paste artifact. Run: scripts\Invoke-ApplyMkmCursorAutomationBootstrap_v1.ps1"
}

$paste = Get-Content -LiteralPath $pastePath -Raw -Encoding UTF8 | ConvertFrom-Json

$idMap = @{
    weekly_doc_sync              = 'MKM Doc Sync v2 (Safe)'
    weekly_test_recovery         = 'MKM Test Recovery v2 (Safe)'
    daily_patrol_failure_triage  = 'MKM Daily Patrol Failure Triage v2'
    internal_pr_review           = 'MKM Internal PR Review v1 (Safe)'
    doc_sync                     = 'MKM Doc Sync v2 (Safe)'
    test_recovery                = 'MKM Test Recovery v2 (Safe)'
    patrol                       = 'MKM Daily Patrol Failure Triage v2'
}

$targetName = $null
if ($idMap.ContainsKey($AutomationId)) {
    $targetName = $idMap[$AutomationId]
}

$row = $null
foreach ($a in $paste.automations) {
    if ($targetName -and $a.name -eq $targetName) { $row = $a; break }
    if ($a.cursor_automation_id -eq $AutomationId) { $row = $a; break }
    if ($a.legacy_name -eq $AutomationId) { $row = $a; break }
}

if (-not $row) {
    throw "Automation not found for id/name: $AutomationId"
}

$text = [string]$row.agent_instructions_paste
Set-Clipboard -Value $text
Write-Host "CLIPBOARD: $($row.name) instructions ($($text.Length) chars)"

if ($OpenEditUrl -and $row.edit_url) {
    Start-Process ([string]$row.edit_url)
    Write-Host "OPENED: $($row.edit_url)"
}

Write-Host "UI checklist:"
Write-Host "  1) Repo -> mkmlab-v2/mkm-destiny-ai-41e38ec6 (not mkm-life)"
Write-Host "  2) Agent instructions -> Ctrl+V (already copied)"
Write-Host "  3) Inactive -> Active"
Write-Host "  4) Copy webhook URL -> reports/cursor_automation_webhook_staging_v1.local.json"
Write-Host "  5) powershell -File scripts\Invoke-SyncMkmCursorAutomationWebhooks_v1.ps1"
exit 0
