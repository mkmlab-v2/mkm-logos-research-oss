#Requires -Version 5.1
<#
.SYNOPSIS
  Solo OSS secret scan — Python patterns (always) + gitleaks (optional).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mkm_secret_scan_v1.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mkm_secret_scan_v1.ps1 -Staged
#>
param(
    [switch]$Staged
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$pyArgs = @("scripts/check_mkm_secret_patterns_v1.py")
if ($Staged) { $pyArgs += "--staged" }
& py @pyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$gitleaks = Get-Command gitleaks -ErrorAction SilentlyContinue
if (-not $gitleaks) {
    $preCommit = Get-Command pre-commit -ErrorAction SilentlyContinue
    if ($preCommit) {
        Write-Host "[INFO] gitleaks not in PATH — falling back to pre-commit hook" -ForegroundColor Cyan
        & pre-commit run gitleaks --all-files
        if ($LASTEXITCODE -ne 0) {
            throw "pre-commit gitleaks failed (exit $LASTEXITCODE)"
        }
        Write-Host "[OK] secret scan (patterns + pre-commit gitleaks)" -ForegroundColor Green
        exit 0
    }
    Write-Host "[WARN] gitleaks not in PATH — pattern scan passed; install: winget install gitleaks OR pre-commit run gitleaks --all-files" -ForegroundColor Yellow
    exit 0
}

$config = Join-Path (Get-Location) ".gitleaks.toml"
$gArgs = @("detect", "--source", ".", "--config", $config, "--no-banner")
if ($Staged) {
    $gArgs += @("--log-opts", "--staged")
}
& gitleaks @gArgs
if ($LASTEXITCODE -ne 0) {
    throw "gitleaks detect failed (exit $LASTEXITCODE)"
}

Write-Host "[OK] secret scan (patterns + gitleaks)" -ForegroundColor Green
