#Requires -Version 5.1
<#
.SYNOPSIS
  Sync Cursor Automation webhook URLs from staging JSON into .env (one-time paste → auto).

.DESCRIPTION
  1) Copy webhook URL from Automations UI (Settings → Webhook URL)
  2) Paste into reports/cursor_automation_webhook_staging_v1.local.json (template created on first -Bootstrap)
  3) Run this script — updates .env MKM_CURSOR_AUTOMATION_WEBHOOK_* keys

.PARAMETER Bootstrap
  Write staging template if missing.

.PARAMETER DryRun
  Show planned .env updates only.

.EXAMPLE
  powershell -File scripts\Invoke-SyncMkmCursorAutomationWebhooks_v1.ps1 -Bootstrap
  # edit reports/cursor_automation_webhook_staging_v1.local.json
  powershell -File scripts\Invoke-SyncMkmCursorAutomationWebhooks_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Bootstrap,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $WorkspaceRoot

$stagingPath = Join-Path $WorkspaceRoot 'reports\cursor_automation_webhook_staging_v1.local.json'
$envPath = Join-Path $WorkspaceRoot '.env'

$template = @{
    schema = 'cursor_automation_webhook_staging_v1'
    note_ko = 'Paste webhook URLs from Automations UI. File is gitignored under reports/.'
    MKM_CURSOR_AUTOMATION_WEBHOOK_DOC_SYNC = ''
    MKM_CURSOR_AUTOMATION_WEBHOOK_TEST_RECOVERY = ''
    MKM_CURSOR_AUTOMATION_WEBHOOK_PATROL = ''
    MKM_CURSOR_AUTOMATION_WEBHOOK_BUGFIX = ''
    MKM_CURSOR_AUTOMATION_WEBHOOK_PR_REVIEW = ''
} | ConvertTo-Json -Depth 4

if ($Bootstrap -or -not (Test-Path -LiteralPath $stagingPath)) {
    [System.IO.File]::WriteAllText($stagingPath, $template, [System.Text.UTF8Encoding]::new($false))
    Write-Host "WROTE template: $stagingPath"
    Write-Host "Next: paste webhook URLs from Automations UI, then re-run without -Bootstrap"
    exit 0
}

$staging = Get-Content -LiteralPath $stagingPath -Raw -Encoding UTF8 | ConvertFrom-Json
$keys = @(
    'MKM_CURSOR_AUTOMATION_WEBHOOK_DOC_SYNC',
    'MKM_CURSOR_AUTOMATION_WEBHOOK_TEST_RECOVERY',
    'MKM_CURSOR_AUTOMATION_WEBHOOK_PATROL',
    'MKM_CURSOR_AUTOMATION_WEBHOOK_BUGFIX',
    'MKM_CURSOR_AUTOMATION_WEBHOOK_PR_REVIEW'
)

$updates = @{}
foreach ($key in $keys) {
    if ($staging.PSObject.Properties.Name -contains $key) {
        $val = [string]$staging.$key
        if ($val.Trim()) { $updates[$key] = $val.Trim() }
    }
}

if ($updates.Count -eq 0) {
    Write-Host "NOOP: staging file has no non-empty webhook URLs"
    exit 2
}

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Missing .env: $envPath"
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.AddRange([System.IO.File]::ReadAllLines($envPath))

foreach ($kv in $updates.GetEnumerator()) {
    $prefix = "$($kv.Key)="
    $newLine = "$prefix$($kv.Value)"
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $t = $lines[$i].Trim()
        if ($t.StartsWith('#') -and $t -match [regex]::Escape($kv.Key)) {
            if (-not $DryRun) { $lines[$i] = $newLine }
            $found = $true
            break
        }
        if ($t.StartsWith($prefix)) {
            if (-not $DryRun) { $lines[$i] = $newLine }
            $found = $true
            break
        }
    }
    if (-not $found) {
        if (-not $DryRun) { $lines.Add($newLine) }
    }
    Write-Host "$(if ($DryRun) { 'DRY ' })SET $($kv.Key)"
}

if ($DryRun) { exit 0 }

[System.IO.File]::WriteAllLines($envPath, $lines.ToArray())
Write-Host "OK: synced $($updates.Count) webhook key(s) into .env"
exit 0
