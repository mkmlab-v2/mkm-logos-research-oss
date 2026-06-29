#Requires -Version 5.1
<#
.SYNOPSIS
  Import and publish n8n webhook for patient intake internal PoC notifications.

.DESCRIPTION
  Webhook path: patient-intake-notification
  Workflow: projects/no1kmedi/ops/n8n/patient_intake_notification_webhook_v1.json

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-PatientIntakeN8nWebhook_v1.ps1
#>
param(
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "C:\workspace" }
Set-Location $root

$workflowName = "patient-intake-notification-webhook"
$workflowId = "PtIntakeNotify01"
$webhookPath = "patient-intake-notification"
$workflowJson = Join-Path $root "projects\no1kmedi\ops\n8n\patient_intake_notification_webhook_v1.json"
$workspaceEnv = Join-Path $root ".env"

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($v) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if ($v) { return $v.Trim() }
    return ""
}

function Read-DotEnvKey([string]$path, [string]$key) {
    if (-not (Test-Path -LiteralPath $path)) { return "" }
    foreach ($line in Get-Content -LiteralPath $path -Encoding UTF8) {
        if ($line -match "^\s*$([regex]::Escape($key))\s*=\s*(.*)$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return ""
}

function Resolve-DedicatedWebhookUrl {
    $explicit = Get-EnvAny "PATIENT_INTAKE_SOLAPI_TEST_WEBHOOK_URL"
    if (-not $explicit) { $explicit = Read-DotEnvKey $workspaceEnv "PATIENT_INTAKE_SOLAPI_TEST_WEBHOOK_URL" }
    if ($explicit) { return $explicit }

    $n8n = Get-EnvAny "N8N_WEBHOOK_URL"
    if (-not $n8n) { $n8n = Read-DotEnvKey $workspaceEnv "N8N_WEBHOOK_URL" }
    if ($n8n -match "^(https?://[^/]+)/webhook/") {
        return ($Matches[1] + "/webhook/" + $webhookPath)
    }
    return "http://srv1101456.hstgr.cloud:5678/webhook/$webhookPath"
}

if (-not (Test-Path -LiteralPath $workflowJson)) {
    Write-Error "Missing workflow JSON: $workflowJson"
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
if (-not $hostName) { $hostName = "vps-mkmlife" }
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$remote = "${user}@${hostName}"
$dedicatedUrl = Resolve-DedicatedWebhookUrl

Write-Host "[patient-intake-n8n] webhook (host only): $($dedicatedUrl -replace '/webhook/.*','/webhook/...')" -ForegroundColor Cyan

if ($WhatIfOnly) {
    Write-Host "[patient-intake-n8n] WhatIf: would import $workflowName on VPS and probe webhook"
    exit 0
}

$extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$sshArgs = @()
if ($extra) { $sshArgs = $extra -split "\s+" | Where-Object { $_ } }

$remoteJson = "/tmp/patient_intake_notification_webhook_v1.json"
& scp @($sshArgs + @($workflowJson, "${remote}:${remoteJson}"))
if ($LASTEXITCODE -ne 0) { throw "scp workflow json failed exit $LASTEXITCODE" }

$remoteCmd = @'
set -e
docker cp '__REMOTE_JSON__' n8n:/tmp/patient_intake_notification_webhook_v1.json
docker exec n8n n8n import:workflow --input=/tmp/patient_intake_notification_webhook_v1.json
docker exec n8n n8n publish:workflow --id=__WORKFLOW_ID__ || true
docker exec n8n n8n update:workflow --id=__WORKFLOW_ID__ --active=true || true
docker restart n8n >/dev/null
sleep 15
echo '[patient-intake-n8n] n8n restarted'
'@ -replace '__REMOTE_JSON__', $remoteJson `
   -replace '__WORKFLOW_ID__', $workflowId

Write-Host "[patient-intake-n8n] VPS import/publish/probe" -ForegroundColor Cyan
$remoteCmd = ($remoteCmd -replace "`r`n", "`n" -replace "`r", "`n").TrimEnd() + "`n"
& ssh @($sshArgs + @($remote, $remoteCmd))
if ($LASTEXITCODE -ne 0) { throw "VPS n8n register failed exit $LASTEXITCODE" }

$probeScript = @"
fetch('$dedicatedUrl',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event:'patient_intake_notification_dry_v1',send_gate:'READY_INTERNAL_POC',notification_lane:'internal_poc',receipt_id:'probe_local'})})
.then(async r=>{const t=await r.text(); if(r.status!==200){console.error('probe_failed',r.status,t); process.exit(1);} console.log('probe_ok',r.status);})
.catch(e=>{console.error(e); process.exit(1);});
"@
& node -e $probeScript
if ($LASTEXITCODE -ne 0) { throw "local webhook probe failed exit $LASTEXITCODE" }

Write-Host "[patient-intake-n8n] OK" -ForegroundColor Green
