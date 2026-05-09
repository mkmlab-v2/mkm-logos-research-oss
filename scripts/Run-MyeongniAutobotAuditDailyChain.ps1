<#
.SYNOPSIS
  Daily chain: build audit summary -> check alert thresholds.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [double]$UnauthorizedRatioThreshold = 0.10,
    [double]$RateLimitedRatioThreshold = 0.20,
    [int]$MinTotal = 20
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

& py "scripts\build_myeongni_autobot_api_audit_summary_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py "scripts\check_myeongni_autobot_api_audit_alert_v1.py" `
    --unauthorized-ratio-threshold $UnauthorizedRatioThreshold `
    --rate-limited-ratio-threshold $RateLimitedRatioThreshold `
    --min-total $MinTotal
$code = $LASTEXITCODE

# Exit code contract:
# 0 = OK/INSUFFICIENT_SAMPLE, 2 = ALERT
exit $code

