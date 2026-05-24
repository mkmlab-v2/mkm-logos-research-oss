#Requires -Version 5.1
<#
.SYNOPSIS
  B-track prophecy headline integrity observation (exit 0 on semantic warnings).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipWebhook
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($WorkspaceRoot) { $WorkspaceRoot } else { Split-Path -Parent $PSScriptRoot }
Set-Location -LiteralPath $repoRoot

$py = Join-Path $env:WINDIR "py.exe"
if (-not (Test-Path -LiteralPath $py)) {
    $py = (Get-Command -Name "py" -ErrorAction Stop).Source
}

$script = Join-Path $PSScriptRoot "check_prophecy_headline_integrity_v1.py"
& $py $script --workspace-root $repoRoot $(if ($SkipWebhook) { "--skip-webhook" })
$exitCode = [int]$LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Error "[CRITICAL] Prophecy headline integrity: infrastructure failure (exit=$exitCode)."
    exit $exitCode
}
Write-Host "prophecy_headline_integrity_ok exit=0" -ForegroundColor Green
exit 0
