# jema-ai.com /smartfarm* -> farm.jema-ai.com (308) via Cloudflare dynamic redirect.
param(
    [string]$ZoneId = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$py = Join-Path $PSScriptRoot "setup_cloudflare_jema_ai_smartfarm_redirect_v1.py"
$args = @()
if ($ZoneId) { $args += @("--zone-id", $ZoneId) }
if ($DryRun) { $args += "--dry-run" }
& py $py @args
exit $LASTEXITCODE
