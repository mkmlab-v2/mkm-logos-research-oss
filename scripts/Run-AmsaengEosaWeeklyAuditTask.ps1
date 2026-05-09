[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

& py (Join-Path $PSScriptRoot "check_cursorrules_template_drift_v1.py")
& py (Join-Path $PSScriptRoot "build_fact_lock_evidence_bundle_v1.py") --append-agent-log
& py (Join-Path $PSScriptRoot "build_amsaeng_eosa_weekly_audit_packet_v1.py")
& py (Join-Path $PSScriptRoot "send_amsaeng_eosa_weekly_alert_v1.py")
