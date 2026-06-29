#Requires -Version 5.1
<#
.SYNOPSIS
  Restore tracked runtime artifact noise so Cursor Git UI stays usable.

.DESCRIPTION
  Daily schedulers refresh many tracked *_latest JSON/MD under docs/final/artifacts and reports/.
  .gitignore does not hide already-tracked files — this script runs `git restore` on porcelain
  paths that match runtime patterns only. Source edits (projects/no1kmedi, scripts/, tests/, etc.)
  are never selected.

.PARAMETER DryRun
  List paths that would be restored; do not run git restore.

.PARAMETER WorkspaceRoot
  Repo root (default C:\workspace).

.PARAMETER OutJson
  Write summary JSON (default reports/git_runtime_artifact_restore_latest.json).

.PARAMETER PorcelainWarnThreshold
  Emit WARN when porcelain count after restore still exceeds this (default 80).

.NOTES
  SSOT policy: AGENTS.md 「로컬 재생성 산출물」·「런타임 JSON 잡음」.
#>
param(
    [switch]$DryRun,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$OutJson = "",
    [int]$PorcelainWarnThreshold = 80
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $WorkspaceRoot "reports\git_runtime_artifact_restore_latest.json"
}

$protectedPrefix = @(
    ".cursor/",
    "projects/no1kmedi/",
    "projects/mkm/",
    "scripts/",
    "tests/",
    "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
    "MISSION_LOG.md",
    "MISSION_LOG.old.md",
    ".env.example"
)

$runtimePatterns = @(
    '^docs/final/artifacts/.*_latest\.(json|md|txt)$',
    '^docs/final/artifacts/.*_latest\.validated\.json$',
    '^docs/final/artifacts/prophecy_proxy_streak_state_v1\.json$',
    '^reports/',
    '^projects/bitcoin-trading/exports/',
    '^projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest\.json$',
    '^projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_.*\.json$',
    '^research/market_data/kospi_daily'
)

function Test-ProtectedPath([string]$Path) {
    $norm = $Path -replace '\\', '/'
    foreach ($p in $protectedPrefix) {
        if ($norm -eq $p -or $norm.StartsWith($p)) { return $true }
    }
    return $false
}

function Test-RuntimeArtifactPath([string]$Path) {
    $norm = $Path -replace '\\', '/'
    if (Test-ProtectedPath $norm) { return $false }
    foreach ($pat in $runtimePatterns) {
        if ($norm -match $pat) { return $true }
    }
    return $false
}

Set-Location -LiteralPath $WorkspaceRoot
if (-not (Test-Path -LiteralPath (Join-Path $WorkspaceRoot ".git"))) {
    throw "Not a git repository: $WorkspaceRoot"
}

$porcelainBefore = @(git status --porcelain)
$beforeCount = $porcelainBefore.Count

$candidates = @()
foreach ($line in $porcelainBefore) {
    if ($line.Length -lt 4) { continue }
    $path = $line.Substring(3).Trim()
    if ($path -match ' -> ') {
        $path = ($path -split ' -> ', 2)[0].Trim()
    }
    if (Test-RuntimeArtifactPath $path) {
        $candidates += $path
    }
}

$restored = @()
$skipped = @()
if ($candidates.Count -gt 0) {
    if ($DryRun) {
        $restored = $candidates
        Write-Host "[dry-run] would restore $($candidates.Count) path(s)" -ForegroundColor Yellow
        $candidates | ForEach-Object { Write-Host "  $_" }
    } else {
        git restore -- @candidates
        if ($LASTEXITCODE -ne 0) { throw "git restore failed with exit $LASTEXITCODE" }
        $restored = $candidates
        Write-Host "Restored $($candidates.Count) runtime artifact path(s)." -ForegroundColor Green
    }
} else {
    Write-Host "No runtime artifact paths to restore." -ForegroundColor Green
}

$porcelainAfter = @(git status --porcelain)
$afterCount = $porcelainAfter.Count

$doc = @{
    schema = "git_runtime_artifact_restore_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    workspace_root = $WorkspaceRoot
    dry_run = [bool]$DryRun
    porcelain_before = $beforeCount
    porcelain_after = $afterCount
    candidate_count = $candidates.Count
    restored_paths = $restored
    protected_prefixes = $protectedPrefix
    runtime_patterns = $runtimePatterns
    ok = $true
}

if ($afterCount -gt $PorcelainWarnThreshold) {
    $doc.warn = "porcelain_after=$afterCount exceeds threshold=$PorcelainWarnThreshold"
    Write-Host "WARN: $($doc.warn)" -ForegroundColor Yellow
}

$outDir = Split-Path -Parent $OutJson
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$doc | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutJson -Encoding utf8
Write-Host "Wrote: $OutJson"
Write-Host "porcelain: $beforeCount -> $afterCount"

exit 0
