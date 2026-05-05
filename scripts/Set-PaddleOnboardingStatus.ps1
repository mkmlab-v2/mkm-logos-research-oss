param(
    [ValidateSet("RUNBOOK_READY", "IN_PROGRESS", "BLOCKED", "VERIFICATION_PENDING", "COMPLETED")]
    [string]$Status,
    [string]$Note = ""
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
$builder = Join-Path $root "scripts\build_paddle_onboarding_status_v1.py"

if (-not (Test-Path -LiteralPath $builder)) {
    throw "Missing builder: $builder"
}

$args = @($builder, "--workspace-root", $root, "--status", $Status)
if (-not [string]::IsNullOrWhiteSpace($Note)) {
    $args += @("--note", $Note)
}

& py @args
if ($LASTEXITCODE -ne 0) {
    throw "Failed to set Paddle onboarding status."
}

Write-Host "Paddle onboarding status updated: $Status" -ForegroundColor Green
