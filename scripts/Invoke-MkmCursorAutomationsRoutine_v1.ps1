#Requires -Version 5.1
<#
.SYNOPSIS
  MKM Cursor Automations D-layer routine — local C-layer smoke + webhook bridge status.

.DESCRIPTION
  SSOT: docs/final/artifacts/mkm_cursor_automations_workflows_v1.json
  Does not create cursor.com automations (human UI). Verifies local substitutes + webhook wiring.

.PARAMETER Mode
  status = report only (default)
  local_doc_sync = run Invoke-MkmDocSyncSafe_v1.ps1
  local_test_recovery = run Invoke-MkmTestRecoverySafe_v1.ps1
  notify_patrol_dry = webhook dry-run patrol_failure

.PARAMETER DryRun
  For status: same as default. For local_*: print command only.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmCursorAutomationsRoutine_v1.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmCursorAutomationsRoutine_v1.ps1 -Mode local_doc_sync
#>
param(
    [ValidateSet('status', 'local_doc_sync', 'local_test_recovery', 'notify_patrol_dry', 'recommended')]
    [string]$Mode = 'status',

    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $WorkspaceRoot

$ssotPath = Join-Path $WorkspaceRoot 'docs\final\artifacts\mkm_cursor_automations_workflows_v1.json'
if (-not (Test-Path -LiteralPath $ssotPath)) {
    throw "Missing SSOT: $ssotPath"
}
$ssot = Get-Content -LiteralPath $ssotPath -Raw -Encoding UTF8 | ConvertFrom-Json

function Test-EnvKeyPresent {
    param([string]$Key)
    if ([Environment]::GetEnvironmentVariable($Key)) { return $true }
    $dotenv = Join-Path $WorkspaceRoot '.env'
    if (-not (Test-Path -LiteralPath $dotenv)) { return $false }
    $prefix = "$Key="
    foreach ($line in [System.IO.File]::ReadAllLines($dotenv)) {
        $t = $line.Trim()
        if ($t -and -not $t.StartsWith('#') -and $t.StartsWith($prefix)) { return $true }
    }
    return $false
}

function Get-DotEnvValue {
    param([string]$Key)
    $envVal = [Environment]::GetEnvironmentVariable($Key)
    if ($envVal) { return $envVal.Trim() }
    $dotenv = Join-Path $WorkspaceRoot '.env'
    if (-not (Test-Path -LiteralPath $dotenv)) { return '' }
    $prefix = "$Key="
    foreach ($line in [System.IO.File]::ReadAllLines($dotenv)) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith('#') -or -not $t.StartsWith($prefix)) { continue }
        return $t.Substring($prefix.Length).Trim()
    }
    return ''
}

$steps = [ordered]@{}
$ok = $true

function Invoke-TrackedStep {
    param([string]$Name, [scriptblock]$Block)
    if ($DryRun) {
        Write-Host "DRY_RUN step: $Name"
        $steps[$Name] = @{ exit_code = 0; dry_run = $true }
        return
    }
    & $Block
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    $steps[$Name] = @{ exit_code = $code }
    if ($code -ne 0) { $script:ok = $false }
}

switch ($Mode) {
    'local_doc_sync' {
        Invoke-TrackedStep 'local_doc_sync' {
            powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot 'scripts\Invoke-MkmDocSyncSafe_v1.ps1') -WorkspaceRoot $WorkspaceRoot
        }
    }
    'local_test_recovery' {
        Invoke-TrackedStep 'local_test_recovery' {
            powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot 'scripts\Invoke-MkmTestRecoverySafe_v1.ps1') -WorkspaceRoot $WorkspaceRoot
        }
    }
    'notify_patrol_dry' {
        Invoke-TrackedStep 'webhook_patrol_dry' {
            powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot 'scripts\Invoke-MkmCursorAutomationWebhook_v1.ps1') `
                -EventKind patrol_failure -Package DailyOpsPatrol -DryRun -WorkspaceRoot $WorkspaceRoot
        }
    }
    'recommended' {
        Invoke-TrackedStep 'bootstrap_tasks' {
            powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot 'scripts\Invoke-ApplyMkmCursorAutomationBootstrap_v1.ps1') -WorkspaceRoot $WorkspaceRoot
        }
        Invoke-TrackedStep 'persona_doc_sync' {
            powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot 'scripts\Invoke-MkmPersonaHealth_v1.ps1') -Persona DocSyncSafe
        }
        Invoke-TrackedStep 'persona_test_recovery' {
            powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot 'scripts\Invoke-MkmPersonaHealth_v1.ps1') -Persona TestRecoverySafe
        }
    }
    default { }
}

$envStatus = [ordered]@{}
foreach ($prop in $ssot.env_keys.PSObject.Properties) {
    $envStatus[$prop.Name] = Test-EnvKeyPresent -Key ([string]$prop.Value)
}

$githubFix = Join-Path $WorkspaceRoot 'reports\cursor_automation_github_fixup_v1_latest.json'
$githubFixOk = Test-Path -LiteralPath $githubFix

$report = [ordered]@{
    schema              = 'mkm_cursor_automations_routine_v1'
    generated_at_utc    = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    mode                = $Mode
    ok                  = $ok
    research_only       = $true
    recommended_mode    = 'local_only'
    automations_mode_env = (Get-DotEnvValue -Key 'MKM_CURSOR_AUTOMATIONS_MODE')
    ssot                = 'docs/final/artifacts/mkm_cursor_automations_workflows_v1.json'
    env_keys_configured = $envStatus
    github_fixup_report = if ($githubFixOk) { 'reports/cursor_automation_github_fixup_v1_latest.json' } else { $null }
    activation_checklist = @($ssot.activation_checklist)
    automations         = @(
        foreach ($a in $ssot.automations) {
            [ordered]@{
                id                  = $a.id
                name                = $a.name
                cursor_automation_id = $a.cursor_automation_id
                trigger             = $a.trigger
                env_key             = $a.env_key
            }
        }
    )
    steps               = $steps
    repro               = @($ssot.repro_commands)
}

$outPath = Join-Path $WorkspaceRoot 'reports\mkm_cursor_automations_routine_latest.json'
$jsonText = $report | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($outPath, $jsonText, [System.Text.UTF8Encoding]::new($false))

Write-Host "WROTE: $outPath"
Write-Host "CURSOR_AUTOMATIONS_ROUTINE_OK=$ok MODE=$Mode"
if (-not $ok) { exit 1 }
exit 0
