#Requires -Version 5.1
<#
.SYNOPSIS
  Import and publish dedicated n8n webhook workflow for compression pilot audit leads.

.DESCRIPTION
  Webhook path: compression-pilot-audit-lead
  Workflow file: projects/no1kmedi/ops/n8n/compression_pilot_audit_lead_webhook_v1.json

  Re-imports workflow JSON on each run (publish + n8n restart). Probes webhook URL locally.
  Writes COMPRESSION_PILOT_AUDIT_LEAD_WEBHOOK_URL to workspace .env when -WriteWorkspaceEnv.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-CompressionPilotAuditN8nWebhook_v1.ps1 -WriteWorkspaceEnv
#>
param(
    [switch]$WriteWorkspaceEnv,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "C:\workspace" }
Set-Location $root

$workflowName = "compression-pilot-audit-lead-webhook"
$workflowId = "CpLdWhk001Audit1"
$webhookPath = "compression-pilot-audit-lead"
$workflowJson = Join-Path $root "projects\no1kmedi\ops\n8n\compression_pilot_audit_lead_webhook_v1.json"
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

function Upsert-DotEnvKey([string]$path, [string]$key, [string]$value) {
    $lines = [System.Collections.Generic.List[string]]@()
    if (Test-Path -LiteralPath $path) {
        $lines = [System.Collections.Generic.List[string]]@(Get-Content -LiteralPath $path -Encoding UTF8)
    }
    $pattern = "^\s*$([regex]::Escape($key))\s*="
    $idx = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) { $idx = $i; break }
    }
    $newLine = "$key=$value"
    if ($idx -ge 0) { $lines[$idx] = $newLine } else { $lines.Add($newLine) }
    Set-Content -LiteralPath $path -Value ($lines -join "`n") -Encoding UTF8 -NoNewline
    Add-Content -LiteralPath $path -Value "`n" -Encoding UTF8
}

function Resolve-DedicatedWebhookUrl {
    $explicit = Get-EnvAny "COMPRESSION_PILOT_AUDIT_LEAD_WEBHOOK_URL"
    if (-not $explicit) { $explicit = Read-DotEnvKey $workspaceEnv "COMPRESSION_PILOT_AUDIT_LEAD_WEBHOOK_URL" }
    if ($explicit -and ($explicit -notmatch "btc-phase1-observe-alert")) { return $explicit }

    $ops = Get-EnvAny "OPS_ALARM_WEBHOOK_URL"
    if (-not $ops) { $ops = Read-DotEnvKey $workspaceEnv "OPS_ALARM_WEBHOOK_URL" }
    if ($ops -match "^(https?://[^/]+)/webhook/") {
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

Write-Host "[compression-pilot-n8n] dedicated webhook (host only): $($dedicatedUrl -replace '/webhook/.*','/webhook/...')" -ForegroundColor Cyan

if ($WhatIfOnly) {
    Write-Host "[compression-pilot-n8n] WhatIf: would import $workflowName on VPS and probe webhook"
    exit 0
}

$extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$sshArgs = @()
if ($extra) { $sshArgs = $extra -split "\s+" | Where-Object { $_ } }

$remoteJson = "/tmp/compression_pilot_audit_lead_webhook_v1.json"
& scp @($sshArgs + @($workflowJson, "${remote}:${remoteJson}"))
if ($LASTEXITCODE -ne 0) { throw "scp workflow json failed exit $LASTEXITCODE" }

$remoteCmd = @'
set -e
docker cp '__REMOTE_JSON__' n8n:/tmp/compression_pilot_audit_lead_webhook_v1.json
docker exec n8n n8n import:workflow --input=/tmp/compression_pilot_audit_lead_webhook_v1.json
docker exec n8n n8n publish:workflow --id=__WORKFLOW_ID__ || true
docker restart n8n >/dev/null
sleep 10
echo '[compression-pilot-n8n] n8n restarted'
'@ -replace '__REMOTE_JSON__', $remoteJson `
   -replace '__WORKFLOW_NAME__', $workflowName `
   -replace '__WORKFLOW_ID__', $workflowId

Write-Host "[compression-pilot-n8n] VPS import/publish/probe" -ForegroundColor Cyan
$remoteCmd = ($remoteCmd -replace "`r`n", "`n" -replace "`r", "`n").TrimEnd() + "`n"
& ssh @($sshArgs + @($remote, $remoteCmd))
if ($LASTEXITCODE -ne 0) { throw "VPS n8n register failed exit $LASTEXITCODE" }

$probeScript = @"
fetch('$dedicatedUrl',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({probe:true,application_id:'probe_local',company_legal_name:'Probe',contact_email:'probe@example.com',primary_domain:'llm_ops',send_gate:'HOLD'})})
.then(async r=>{const t=await r.text(); if(r.status!==200){console.error('probe_failed',r.status,t); process.exit(1);} console.log('probe_ok',r.status);})
.catch(e=>{console.error(e); process.exit(1);});
"@
& node -e $probeScript
if ($LASTEXITCODE -ne 0) { throw "local webhook probe failed exit $LASTEXITCODE" }

if ($WriteWorkspaceEnv) {
    Upsert-DotEnvKey $workspaceEnv "COMPRESSION_PILOT_AUDIT_LEAD_WEBHOOK_URL" $dedicatedUrl
    Write-Host "[compression-pilot-n8n] updated $workspaceEnv COMPRESSION_PILOT_AUDIT_LEAD_WEBHOOK_URL" -ForegroundColor Green
}

Write-Host "[compression-pilot-n8n] OK" -ForegroundColor Green
