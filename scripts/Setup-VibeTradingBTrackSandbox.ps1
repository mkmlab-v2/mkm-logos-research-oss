<#
.SYNOPSIS
  Prepare isolated Vibe-Trading sandbox for B-Track research.

.DESCRIPTION
  Clones HKUDS/Vibe-Trading into a dedicated research folder and writes
  guardrail notes to prevent Track A/prod linkage.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$RepoUrl = "https://github.com/HKUDS/Vibe-Trading.git",
    [string]$SandboxRoot = "research\vibe_trading_btrack_sandbox",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$sandboxPath = Join-Path $WorkspaceRoot $SandboxRoot
$repoPath = Join-Path $sandboxPath "Vibe-Trading"
$notesPath = Join-Path $sandboxPath "MKM_BTRACK_GUARDRAILS.md"

if ($DryRun) {
    Write-Host "[DRYRUN] workspace: $WorkspaceRoot"
    Write-Host "[DRYRUN] sandbox:   $sandboxPath"
    Write-Host "[DRYRUN] repo path: $repoPath"
    Write-Host "[DRYRUN] notes:     $notesPath"
    Write-Host "[DRYRUN] would ensure sandbox directory exists"
    if (-not (Test-Path -LiteralPath $repoPath)) {
        Write-Host "[DRYRUN] would clone: $RepoUrl"
    } else {
        Write-Host "[DRYRUN] repo exists; would skip clone"
    }
    Write-Host "[DRYRUN] would write/update guardrails markdown"
    exit 0
}

if (-not (Test-Path -LiteralPath $sandboxPath)) {
    New-Item -ItemType Directory -Path $sandboxPath -Force | Out-Null
}

if (-not (Test-Path -LiteralPath $repoPath)) {
    git clone $RepoUrl $repoPath
} else {
    Write-Host "Repo already exists: $repoPath"
}

$guardrails = @"
# MKM B-Track Guardrails for Vibe-Trading

- Scope: research_only / observation_only.
- Never auto-bridge Vibe outputs into Track A or live trading.
- Any candidate strategy must be reimplemented in MKM SSOT scripts/artifacts.
- Promotion requires explicit human approval and existing MKM gate checks.
- Keep deterministic evidence: path/key/value logs and fixed evaluation windows.
"@

Set-Content -LiteralPath $notesPath -Value $guardrails -Encoding UTF8

Write-Host "Sandbox ready: $sandboxPath"
Write-Host "Repo path: $repoPath"
Write-Host "Guardrails: $notesPath"
