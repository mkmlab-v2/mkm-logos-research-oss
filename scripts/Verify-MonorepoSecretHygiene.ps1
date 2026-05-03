<#
.SYNOPSIS
  Low-risk checks: .env not tracked, gitignore covers secrets hub paths.

.DESCRIPTION
  Does not read or print .env contents. Exit 0 if OK; exit 1 if .env is tracked or ignore missing.
  SSOT pointers: .gitignore (.env), scripts/security_agent_manager.py, scripts/Invoke-EncryptedSecretStore.ps1
#>
param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $RepoRoot

Write-Host "=== Monorepo secret hygiene (read-only) ===" -ForegroundColor Cyan
Write-Host "repo: $RepoRoot"
Write-Host ""

$tracked = @(git ls-files --cached -- ".env" 2>$null)
if ($tracked.Count -gt 0) {
  Write-Host "[FAIL] .env is tracked by Git. Remove from index: git rm --cached .env (keep local file)." -ForegroundColor Red
  exit 1
}

$chk = & git check-ignore -q .env 2>$null; $ignored = ($LASTEXITCODE -eq 0)
if (-not $ignored) {
  Write-Host "[FAIL] .env is not ignored — fix root .gitignore (expect line: .env)." -ForegroundColor Red
  exit 1
}

Write-Host "[ok] .env is not tracked and is gitignored." -ForegroundColor Green

$gitignore = Join-Path $RepoRoot ".gitignore"
if (-not (Test-Path -LiteralPath $gitignore)) {
  Write-Host "[warn] Missing .gitignore at repo root." -ForegroundColor Yellow
} else {
  $gi = Get-Content -LiteralPath $gitignore -Raw -ErrorAction SilentlyContinue
  if ($gi -notmatch '(?m)^\.env\s*$') {
    Write-Host "[warn] Root .gitignore may lack a standalone `.env` line — verify manually." -ForegroundColor Yellow
  }
}

Write-Host ""
Write-Host "Optional (Windows): DPAPI store via scripts/Invoke-EncryptedSecretStore.ps1; bridge: scripts/security_agent_manager.py"
Write-Host "Trading profile (no secrets printed): projects/bitcoin-trading/scripts/preflight_live_trading_readiness.ps1"
exit 0
