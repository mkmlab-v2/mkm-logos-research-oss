<#
.SYNOPSIS
  Daily chain: build compose audit summary -> check alert thresholds.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [double]$Non200RatioThreshold = 0.10,
    [int]$MinTotal = 20
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

& py "scripts\build_mkm_compose_api_audit_summary_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py "scripts\check_mkm_compose_api_audit_alert_v1.py" `
    --non-200-ratio-threshold $Non200RatioThreshold `
    --min-total $MinTotal
$code = $LASTEXITCODE

# Exit code contract:
# 0 = OK/INSUFFICIENT_SAMPLE, 2 = ALERT
exit $code
