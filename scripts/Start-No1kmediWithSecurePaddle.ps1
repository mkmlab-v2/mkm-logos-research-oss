[CmdletBinding()]
param(
    [ValidateSet("dev", "build", "start")]
    [string]$Mode = "dev"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$appDir = Join-Path $root "projects/no1kmedi"
$loader = Join-Path $PSScriptRoot "Use-PaddleSecureSession.ps1"

if (-not (Test-Path -LiteralPath $appDir)) {
    throw "App directory not found: $appDir"
}
if (-not (Test-Path -LiteralPath $loader)) {
    throw "Secure loader not found: $loader"
}

Write-Host "=== Loading secure Paddle env (process scope) ===" -ForegroundColor Cyan
# Run loader in the same PowerShell process so env vars remain available to npm/Next.js.
& $loader

Push-Location $appDir
try {
    switch ($Mode) {
        "dev" { npm run dev }
        "build" { npm run build }
        "start" { npm run start }
    }
}
finally {
    Pop-Location
}

