[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $PSScriptRoot "security_integrity_monitor_v1.py"
$manifestPath = Join-Path $repoRoot "reports\security_integrity_manifest_v1.json"
$statusPath = Join-Path $repoRoot "reports\security_integrity_status_latest.json"

if (-not (Test-Path -LiteralPath $manifestPath)) {
    & py $scriptPath --mode snapshot --manifest-path $manifestPath | Out-Null
}

& py $scriptPath --mode check --manifest-path $manifestPath --status-path $statusPath
