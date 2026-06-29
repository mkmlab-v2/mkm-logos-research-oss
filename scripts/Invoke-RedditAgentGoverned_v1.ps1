# Governed Reddit agent — Fact-Lock R1–R6 (B-track · send_gate HOLD).
#
# Usage:
#   powershell -File scripts\Invoke-RedditAgentGoverned_v1.ps1 -Action preflight
#   powershell -File scripts\Invoke-RedditAgentGoverned_v1.ps1 -Action cleanup
#   powershell -File scripts\Invoke-RedditAgentGoverned_v1.ps1 -Action post -Pack universal_root -DryRun
# Live post (PRAW only):
#   powershell -File scripts\Invoke-RedditAgentGoverned_v1.ps1 -Action post -Pack universal_root -AcknowledgeSend
#
param(
    [ValidateSet('preflight', 'cleanup', 'post')]
    [string]$Action = 'preflight',
    [ValidateSet('bible_topology', 'universal_root', '')]
    [string]$Pack = '',
    [ValidateSet('praw', 'browser')]
    [string]$Via = 'praw',
    [switch]$DryRun,
    [switch]$AcknowledgeSend,
    [switch]$RedditOnly,
    [switch]$CleanupFirst
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$args = @('scripts/run_reddit_agent_governed_v1.py', $Action)
if ($Pack) { $args += @('--pack', $Pack) }
$args += @('--via', $Via)
if ($DryRun) { $args += '--dry-run' }
if ($AcknowledgeSend) { $args += '--acknowledge-send' }
if ($RedditOnly) { $args += '--reddit-only' }
if ($CleanupFirst) { $args += '--cleanup-first' }

Write-Host '==> run_reddit_agent_governed_v1.py' -ForegroundColor Cyan
& py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'OK: reports/reddit_agent_run_v1_latest.json' -ForegroundColor Green
