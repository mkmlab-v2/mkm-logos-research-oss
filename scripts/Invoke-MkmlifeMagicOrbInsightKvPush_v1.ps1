# Push magic_orb insight payloads to mkmlife KV via POST webhook ([HYPO] B-track).
param(
    [string]$BaseUrl = "https://mkmlife.com",
    [switch]$DryRun,
    [switch]$LocalDev
)

$ErrorActionPreference = "Stop"
$root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT } else { "C:\workspace" }
Set-Location $root

if ($LocalDev) { $BaseUrl = "http://127.0.0.1:3105" }

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$args = @("-3", "scripts/push_magic_orb_insight_webhook_v1.py", "--base-url", $BaseUrl, "--push-all-by-query")
if ($DryRun) { $args += "--dry-run" }

& $py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# latest last (overwrites LATEST_KEY)
$latestArgs = @("-3", "scripts/push_magic_orb_insight_webhook_v1.py", "--base-url", $BaseUrl)
if ($DryRun) { $latestArgs += "--dry-run" }
& $py @latestArgs
exit $LASTEXITCODE
