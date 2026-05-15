#Requires -Version 5.1
<#
.SYNOPSIS
  Sequential ops bundle with minimal cross-chat collision risk.

.DESCRIPTION
  Skips: git fetch / origin-main sync, Vault mirror, git push.
  Runs: security check (snapshot+recheck only if RED), Git snapshot JSON in reports/,
        fact-safe risk profile TTL refresh (repo source, default; before health+trading),
        workspace health (light), trading observation, B-track weekly + 1 autopush,
        protective guard, unified snapshot, Athena smoke, agent decision log.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipRiskProfileSync
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

Write-Host "==> 1/11 security_integrity check" -ForegroundColor Cyan
py scripts/security_integrity_monitor_v1.py --mode check
if ($LASTEXITCODE -ne 0) {
    Write-Host "[warn] security not GREEN; refreshing baseline snapshot then re-check" -ForegroundColor Yellow
    py scripts/security_integrity_monitor_v1.py --mode snapshot
    py scripts/security_integrity_monitor_v1.py --mode check
    if ($LASTEXITCODE -ne 0) { throw "security_integrity still not GREEN after snapshot" }
}

Write-Host "==> 2/11 reports checkpoint JSON (no fetch/push)" -ForegroundColor Cyan
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
$ahead = 0
$behind = 0
$null = git rev-parse --verify "origin/main" 2>$null
if ($LASTEXITCODE -eq 0) {
    $ahead = [int]((git rev-list --count "origin/main..HEAD").Trim())
    $behind = [int]((git rev-list --count "HEAD..origin/main").Trim())
}
$dirty = (git status --porcelain | Measure-Object -Line).Lines
$cp = [ordered]@{
    schema                 = "ops_sequential_run_checkpoint_v1"
    generated_at_utc       = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    collision_safe_profile = "no_fetch_no_vault_mirror_no_push"
    git                    = @{
        branch              = $branch
        ahead_of_origin_main = $ahead
        behind_origin_main   = $behind
        porcelain_lines      = $dirty
    }
}
New-Item -ItemType Directory -Force -Path (Join-Path $WorkspaceRoot "reports") | Out-Null
($cp | ConvertTo-Json -Depth 6) + "`n" | Set-Content -LiteralPath (Join-Path $WorkspaceRoot "reports/ops_sequential_run_checkpoint_v1.json") -Encoding utf8
Write-Host "WROTE reports/ops_sequential_run_checkpoint_v1.json"

if (-not $SkipRiskProfileSync) {
    Write-Host "==> 3/11 sync fact-safe risk profile (repo TTL; before health + GO/NO_GO)" -ForegroundColor Cyan
    py scripts/sync_fact_safe_risk_profile.py --repo-source
    if ($LASTEXITCODE -ne 0) { throw "sync_fact_safe_risk_profile exit $LASTEXITCODE" }
} else {
    Write-Host "==> 3/11 sync fact-safe risk profile [skipped -SkipRiskProfileSync]" -ForegroundColor Yellow
}

Write-Host "==> 4/11 workspace automation health (light)" -ForegroundColor Cyan
& pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts/run_workspace_automation_health.ps1") `
    -WorkspaceRoot $WorkspaceRoot `
    -IncludeGitSanity `
    -SkipVaultMirror `
    -SkipMkmMemoryInventory `
    -IncludeProphecyEvolutionWatchdogSmoke `
    -IncludeMcpHygieneProbe

Write-Host "==> 5/11 Run-TradingObservationLoop" -ForegroundColor Cyan
& pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts/Run-TradingObservationLoop.ps1")

Write-Host "==> 6/11 B-track weekly" -ForegroundColor Cyan
& pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts/Run-BtrackControlTowerOps.ps1") -Mode weekly

Write-Host "==> 7/11 B-track autopush x1" -ForegroundColor Cyan
& pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts/Run-BtrackControlTowerOps.ps1") -Mode autopush -MaxRuns 1 -CooldownSeconds 0

Write-Host "==> 8/11 protective coverage guard" -ForegroundColor Cyan
& pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts/Run-ProtectiveCoverageGuardTask.ps1")

Write-Host "==> 9/11 unified state snapshot" -ForegroundColor Cyan
py scripts/build_unified_state_snapshot_v1.py

Write-Host "==> 10/11 Athena execution governance smoke" -ForegroundColor Cyan
py scripts/check_athena_execution_governance_smoke_v1.py

Write-Host "==> 11/11 agent decision log" -ForegroundColor Cyan
py scripts/log_agent_decision.py `
    --mission-id sequential_safe_ops_v1 `
    --stage Report `
    --decision sequential_other_chat_safe_bundle_ok `
    --evidence-path reports/ops_sequential_run_checkpoint_v1.json `
    --actor cursor-agent `
    --risk-level low `
    --note "run_sequential_ops_other_chat_safe_v1.ps1: no fetch/vault/push; repo_risk_sync+health+trading+btrack+protective+unified+athena (-SkipRiskProfileSync omits sync)"

Write-Host "[ok] sequential other-chat-safe bundle complete" -ForegroundColor Green
exit 0
