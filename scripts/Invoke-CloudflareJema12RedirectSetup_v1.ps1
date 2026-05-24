# Apply jema12.com → jema-ai.com 301 via Cloudflare API (or print manual steps).
param(
    [string]$ZoneId = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$py = Join-Path $PSScriptRoot "setup_cloudflare_apex_redirect_v1.py"
$args = @("--apex", "jema12.com", "--target-host", "jema-ai.com")
if ($ZoneId) { $args += @("--zone-id", $ZoneId) }
if ($DryRun) { $args += "--dry-run" }
& py $py @args
exit $LASTEXITCODE
