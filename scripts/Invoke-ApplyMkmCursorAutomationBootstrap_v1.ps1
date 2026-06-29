#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot: local C-layer 자동화 등록 + UI 붙여넣기 artifact + (선택) webhook staging.

.DESCRIPTION
  Cursor Automations UI는 OAuth/레포 선택을 사람만 할 수 있음.
  이 스크립트는 클라우드 없이도 동일 Doc Sync/Test Recovery를 PC에서 자동 실행하게 함.

.PARAMETER SkipTaskRegister
  Skip Windows scheduled task registration.

.PARAMETER OpenUi
  Open cursor.com automation edit URLs in default browser.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ApplyMkmCursorAutomationBootstrap_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipTaskRegister,
    [switch]$OpenUi
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $WorkspaceRoot

$ssotPath = Join-Path $WorkspaceRoot 'docs\final\artifacts\mkm_cursor_automations_workflows_v1.json'
$ssot = Get-Content -LiteralPath $ssotPath -Raw -Encoding UTF8 | ConvertFrom-Json

$steps = [ordered]@{}
$ok = $true

function Step {
    param([string]$Name, [scriptblock]$Block)
    & $Block
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    $steps[$Name] = $code
    if ($code -ne 0) { $script:ok = $false }
}

if (-not $SkipTaskRegister) {
    Step 'register_doc_sync_weekly' {
        powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot 'scripts\Register-MkmDocSyncSafeWeeklyTask.ps1') -WorkspaceRoot $WorkspaceRoot
    }
    Step 'register_test_recovery_weekly' {
        powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot 'scripts\Register-MkmTestRecoverySafeWeeklyTask.ps1') -WorkspaceRoot $WorkspaceRoot
    }
}

Step 'webhook_staging_bootstrap' {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot 'scripts\Invoke-SyncMkmCursorAutomationWebhooks_v1.ps1') -Bootstrap -WorkspaceRoot $WorkspaceRoot
}

$paste = [ordered]@{
    schema = 'mkm_cursor_automation_ui_paste_v1'
    generated_at_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    note_ko = 'Automations UI 수동 최소화: repo는 mkmlab-v2/mkm-destiny-ai-41e38ec6 (mkm-life X). Memories 끄거나 유지 가능 — MKM 장기기억은 디스크 SSOT.'
    wrong_repo_warning = 'mkm-life on main → change to mkmlab-v2/mkm-destiny-ai-41e38ec6'
    automations = @(
        foreach ($a in $ssot.automations) {
            [ordered]@{
                name = $a.name
                legacy_name = $a.legacy_name
                cursor_automation_id = $a.cursor_automation_id
                edit_url = if ($a.cursor_automation_id) { "https://cursor.com/automations/$($a.cursor_automation_id)" } else { $null }
                agent_instructions_paste = $a.instructions + ' ' + $ssot.shared_prompt_footer
                toggle_active = $true
            }
        }
    )
}

$pastePath = Join-Path $WorkspaceRoot 'docs\final\artifacts\mkm_cursor_automation_ui_paste_v1.json'
[System.IO.File]::WriteAllText($pastePath, ($paste | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))
Write-Host "WROTE: $pastePath"

if ($OpenUi) {
    foreach ($a in $paste.automations) {
        if ($a.edit_url) {
            Start-Process $a.edit_url
            Start-Sleep -Milliseconds 800
        }
    }
}

$report = [ordered]@{
    schema = 'mkm_cursor_automation_bootstrap_v1'
    generated_at_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    ok = $ok
    local_tasks_registered = -not $SkipTaskRegister
    paste_artifact = 'docs/final/artifacts/mkm_cursor_automation_ui_paste_v1.json'
    webhook_staging = 'reports/cursor_automation_webhook_staging_v1.local.json'
    cloud_manual_only = @(
        'Automations repo picker (GitHub App)',
        'Generate auth header (1 click)',
        'Toggle Inactive → Active'
    )
    fully_automated_local = @(
        'MKM_DocSync_Safe_Weekly (Sunday 09:00)',
        'MKM_TestRecovery_Safe_Weekly (Saturday 08:00)',
        'Invoke-MkmPersonaHealth_v1.ps1 -Persona DocSyncSafe|TestRecoverySafe'
    )
    steps = $steps
}

$outPath = Join-Path $WorkspaceRoot 'reports\mkm_cursor_automation_bootstrap_latest.json'
[System.IO.File]::WriteAllText($outPath, ($report | ConvertTo-Json -Depth 6), [System.Text.UTF8Encoding]::new($false))
Write-Host "WROTE: $outPath"
Write-Host "BOOTSTRAP_OK=$ok"
if (-not $ok) { exit 1 }
exit 0
