# jema-ai.com /smartfarm* -> farm.jema-ai.com (308) via Cloudflare dynamic redirect.
param(
    [string]$ZoneId = "",
    [switch]$DryRun,
    [switch]$SkipTriage
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not $SkipTriage) {
    Write-Host "== CF token roles triage (jema-ai redirect) ==" -ForegroundColor Cyan
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & py scripts/check_cloudflare_token_roles_v1.py *> $null
    $triageExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    Get-Content (Join-Path $root "reports/cloudflare_token_roles_triage_v1_latest.json") -Raw | Write-Host
    if ($triageExit -gt 2) { exit $triageExit }
    $triagePath = Join-Path $root "reports/cloudflare_token_roles_triage_v1_latest.json"
    if ((Test-Path $triagePath) -and -not $DryRun) {
        $triage = Get-Content $triagePath -Raw | ConvertFrom-Json
        $ready = $triage.jema_ai_dynamic_redirect.automation_ready
        if (-not $ready) {
            Write-Host "[smartfarm-cf] STOP: jema_ai_dynamic_redirect not ready — fix scope per jema_ai_redirect_guard (no PUT repeat)." -ForegroundColor Yellow
            exit 2
        }
    }
}

$py = Join-Path $PSScriptRoot "setup_cloudflare_jema_ai_smartfarm_redirect_v1.py"
$args = @()
if ($ZoneId) { $args += @("--zone-id", $ZoneId) }
if ($DryRun) { $args += "--dry-run" }
& py $py @args
exit $LASTEXITCODE
