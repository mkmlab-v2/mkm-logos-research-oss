#Requires -Version 5.1
<#
.SYNOPSIS
  POST MKM patrol/package events to Cursor Automation webhook URLs (D-layer bridge).

.DESCRIPTION
  SSOT: docs/final/artifacts/mkm_cursor_automations_workflows_v1.json
  Env: MKM_CURSOR_AUTOMATION_WEBHOOK_PATROL | _BUGFIX | _DOC_SYNC | _TEST_RECOVERY | _PR_REVIEW
  Does not replace C-layer exit codes — notification/triage only.

.PARAMETER EventKind
  patrol_failure | doc_sync | test_recovery | pr_review | custom

.PARAMETER Package
  Command package name when EventKind is patrol_failure (DailyOpsPatrol, etc.).

.PARAMETER PasteLine
  Optional 1-line summary from Invoke-MkmCommandPackage paste helper.

.PARAMETER PayloadJson
  Optional raw JSON string merged into outbound body.

.PARAMETER DryRun
  Resolve URL + build payload only; no HTTP POST.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmCursorAutomationWebhook_v1.ps1 -EventKind patrol_failure -Package DailyOpsPatrol -DryRun
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('patrol_failure', 'doc_sync', 'test_recovery', 'pr_review', 'custom')]
    [string]$EventKind,

    [string]$WorkspaceRoot = "C:\workspace",
    [string]$Package = "",
    [string]$PasteLine = "",
    [string]$PayloadJson = "",
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $WorkspaceRoot

$ssotPath = Join-Path $WorkspaceRoot 'docs\final\artifacts\mkm_cursor_automations_workflows_v1.json'
if (-not (Test-Path -LiteralPath $ssotPath)) {
    throw "Missing SSOT: $ssotPath"
}
$ssot = Get-Content -LiteralPath $ssotPath -Raw -Encoding UTF8 | ConvertFrom-Json

function Get-DotEnvValue {
    param([string]$Key)
    $envVal = [Environment]::GetEnvironmentVariable($Key)
    if ($envVal) { return $envVal.Trim() }
    $dotenv = Join-Path $WorkspaceRoot '.env'
    if (-not (Test-Path -LiteralPath $dotenv)) { return '' }
    $prefix = "$Key="
    foreach ($raw in [System.IO.File]::ReadAllLines($dotenv)) {
        $line = $raw.Trim()
        if (-not $line -or $line.StartsWith('#') -or -not $line.StartsWith($prefix)) { continue }
        $value = $line.Substring($prefix.Length).Trim()
        if ($value -match ' #') { $value = ($value -split ' #', 2)[0].Trim() }
        if ($value.Length -ge 2 -and $value[0] -eq $value[-1] -and $value[0] -in @("'", '"')) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        return $value.Trim()
    }
    return ''
}

$automationMode = (Get-DotEnvValue -Key 'MKM_CURSOR_AUTOMATIONS_MODE').ToLowerInvariant()
if (-not $automationMode) { $automationMode = 'local_only' }
if ($automationMode -eq 'local_only' -and -not $DryRun) {
    $skipBody = [ordered]@{
        schema = 'mkm_cursor_automation_webhook_v1'
        event = $EventKind
        skipped = $true
        reason = 'MKM_CURSOR_AUTOMATIONS_MODE=local_only (recommended C-layer)'
        ts_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    } | ConvertTo-Json -Depth 4
    $outDir = Join-Path $WorkspaceRoot 'reports'
    if (-not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
    $outPath = Join-Path $outDir 'mkm_cursor_automation_webhook_latest.json'
    [System.IO.File]::WriteAllText($outPath, $skipBody, [System.Text.UTF8Encoding]::new($false))
    Write-Host "WEBHOOK_SKIP: local_only mode (recommended)"
    exit 0
}

$envKeyMap = @{
    patrol_failure = @('MKM_CURSOR_AUTOMATION_WEBHOOK_PATROL', 'MKM_CURSOR_AUTOMATION_WEBHOOK_BUGFIX')
    doc_sync       = @('MKM_CURSOR_AUTOMATION_WEBHOOK_DOC_SYNC')
    test_recovery  = @('MKM_CURSOR_AUTOMATION_WEBHOOK_TEST_RECOVERY')
    pr_review      = @('MKM_CURSOR_AUTOMATION_WEBHOOK_PR_REVIEW')
    custom         = @('MKM_CURSOR_AUTOMATION_WEBHOOK_PATROL', 'MKM_CURSOR_AUTOMATION_WEBHOOK_BUGFIX')
}

$webhookUrl = ''
foreach ($key in $envKeyMap[$EventKind]) {
    $webhookUrl = Get-DotEnvValue -Key $key
    if ($webhookUrl) { break }
}
if (-not $webhookUrl) {
    $webhookUrl = Get-DotEnvValue -Key 'OPS_ALARM_WEBHOOK_URL'
}

$pasteArtifact = Join-Path $WorkspaceRoot 'reports\mkm_command_package_paste_latest.json'
$pasteObj = $null
if (Test-Path -LiteralPath $pasteArtifact) {
    try { $pasteObj = Get-Content -LiteralPath $pasteArtifact -Raw -Encoding UTF8 | ConvertFrom-Json } catch { }
}

$automationMeta = $null
foreach ($row in $ssot.automations) {
    if ($EventKind -eq 'patrol_failure' -and $row.id -eq 'daily_patrol_failure_triage') { $automationMeta = $row; break }
    if ($EventKind -eq 'doc_sync' -and $row.id -eq 'weekly_doc_sync') { $automationMeta = $row; break }
    if ($EventKind -eq 'test_recovery' -and $row.id -eq 'weekly_test_recovery') { $automationMeta = $row; break }
    if ($EventKind -eq 'pr_review' -and $row.id -eq 'internal_pr_review') { $automationMeta = $row; break }
}

$body = [ordered]@{
    schema           = 'mkm_cursor_automation_webhook_v1'
    event            = $EventKind
    ts_utc           = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    workspace_root   = $WorkspaceRoot
    package          = $Package
    paste_line       = if ($PasteLine) { $PasteLine } elseif ($pasteObj -and $pasteObj.paste_line) { [string]$pasteObj.paste_line } else { '' }
    automation_name  = if ($automationMeta) { [string]$automationMeta.name } else { '' }
    automation_id    = if ($automationMeta -and $automationMeta.cursor_automation_id) { [string]$automationMeta.cursor_automation_id } else { '' }
    instructions_ref = 'docs/final/artifacts/mkm_cursor_automations_workflows_v1.json'
    research_only    = $true
    track            = 'B'
    note_ko          = 'D-layer triage only — C-layer exit code remains SSOT'
}

if ($PayloadJson) {
    try {
        $extra = $PayloadJson | ConvertFrom-Json
        foreach ($prop in $extra.PSObject.Properties) {
            $body[$prop.Name] = $prop.Value
        }
    }
    catch {
        $body['payload_raw'] = $PayloadJson
    }
}

$outDir = Join-Path $WorkspaceRoot 'reports'
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$outPath = Join-Path $outDir 'mkm_cursor_automation_webhook_latest.json'
$jsonText = $body | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($outPath, $jsonText, [System.Text.UTF8Encoding]::new($false))
Write-Host "WROTE: $outPath"

if (-not $webhookUrl) {
    Write-Host "WEBHOOK_SKIP: no URL (set MKM_CURSOR_AUTOMATION_WEBHOOK_* or OPS_ALARM_WEBHOOK_URL)" -ForegroundColor Yellow
    exit 2
}

if ($DryRun) {
    Write-Host "DRY_RUN: would POST to $($webhookUrl.Substring(0, [Math]::Min(48, $webhookUrl.Length)))..."
    exit 0
}

try {
    $null = Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $jsonText -ContentType 'application/json; charset=utf-8' -TimeoutSec 30
    Write-Host "WEBHOOK_OK: $EventKind"
    exit 0
}
catch {
    Write-Host "WEBHOOK_FAIL: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
