#Requires -Version 5.1
<#
.SYNOPSIS
  Solo developer: merge the current (or named) feature branch into local main and push to gitea/internal.

.DESCRIPTION
  Your workspace uses internal-first publication (scripts/push-internal.ps1). Integration target for day-to-day work
  is gitea/main (same bare repo as remote "internal").

  If refs/heads/main is checked out in another git worktree (common here), this script finds that path via
  `git worktree list`, runs merge + push there. Primary repo stays on your feature branch.

.PARAMETER FeatureBranch
  Branch to merge into main. Default: current branch.

.PARAMETER IntegrationRemote
  Default: gitea (falls back to internal if gitea missing).

.PARAMETER MainWorktreePath
  Override path where branch "main" is checked out. Autodetected if omitted.

.PARAMETER SkipVerify
  Skip scripts/verify_p0_constitution_gate_paths.ps1 before push.

.PARAMETER DryRun
  Print commands only.

.NOTES
  Run from C:\workspace (repo root). Requires clean working trees for both the feature checkout and main checkout.
#>

param(
    [string]$FeatureBranch = "",
    [string]$IntegrationRemote = "gitea",
    [string]$MainWorktreePath = "",
    [switch]$SkipVerify,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repoRoot = "C:\workspace"
if (-not (Test-Path (Join-Path $repoRoot ".git"))) {
    throw "Expected git repo at $repoRoot"
}
Set-Location $repoRoot

function Get-GitRemoteNames {
    $names = @()
    (git remote) | ForEach-Object { $names += $_.Trim() }
    return $names
}

function Resolve-IntegrationRemote {
    param([string]$Preferred)
    $remotes = Get-GitRemoteNames
    if ($remotes -contains $Preferred) { return $Preferred }
    if ($Preferred -eq "gitea" -and $remotes -contains "internal") {
        Write-Host "[INFO] Remote 'gitea' not found; using 'internal'." -ForegroundColor DarkCyan
        return "internal"
    }
    throw "No suitable remote. Expected gitea or internal. Found: $($remotes -join ', ')"
}

function Get-MainWorktreePath {
    param([string]$Override)
    if ($Override) {
        if (-not (Test-Path (Join-Path $Override ".git"))) {
            # worktree root contains .git file pointer
            $gitFile = Join-Path $Override ".git"
            if (-not (Test-Path $gitFile)) { throw "Main worktree path invalid: $Override" }
        }
        return $Override
    }
    $lines = git worktree list
    foreach ($line in $lines) {
        if ($line -match "^(?<path>\S+)\s+\S+\s+\[main\]\s*$") {
            return $matches["path"]
        }
    }
    return $null
}

function Assert-CleanWorktree {
    param([string]$Path)
    $prev = Get-Location
    try {
        Set-Location $Path
        $st = (git status --porcelain)
        if ($st) {
            throw "Working tree not clean: $Path`n$st"
        }
    }
    finally {
        Set-Location $prev
    }
}

$remoteName = Resolve-IntegrationRemote -Preferred $IntegrationRemote

if (-not $FeatureBranch) {
    $FeatureBranch = (git rev-parse --abbrev-ref HEAD).Trim()
}
if ($FeatureBranch -eq "main") {
    throw "Already on main; switch to a feature branch first or merge manually."
}

$mainPath = Get-MainWorktreePath -Override $MainWorktreePath
if (-not $mainPath) {
    throw "Could not find a worktree with [main]. Create one (git worktree add ...) or pass -MainWorktreePath."
}

Write-Host "[INFO] Repo root:     $repoRoot" -ForegroundColor Cyan
Write-Host "[INFO] Feature branch: $FeatureBranch" -ForegroundColor Cyan
Write-Host "[INFO] Main worktree:  $mainPath" -ForegroundColor Cyan
Write-Host "[INFO] Push remote:    $remoteName" -ForegroundColor Cyan

if (-not $DryRun) {
    Assert-CleanWorktree -Path $repoRoot
    Assert-CleanWorktree -Path $mainPath
}
else {
    Write-Host "[DRY] Skipping working-tree clean check." -ForegroundColor DarkGray
}

$steps = @(
    @{ Desc = "fetch $remoteName"; Cmd = "git -C `"$mainPath`" fetch $remoteName" },
    @{ Desc = "update main from $remoteName/main"; Cmd = "git -C `"$mainPath`" merge --ff-only $remoteName/main" },
    @{ Desc = "merge feature $FeatureBranch"; Cmd = "git -C `"$mainPath`" merge $FeatureBranch --no-edit" }
)

foreach ($s in $steps) {
    Write-Host "[STEP] $($s.Desc)" -ForegroundColor Yellow
    if ($DryRun) {
        Write-Host "  DRY: $($s.Cmd)"
        continue
    }
    cmd /c $s.Cmd
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $($s.Desc) (exit $LASTEXITCODE)"
    }
}

if (-not $SkipVerify) {
    Write-Host "[STEP] verify_p0_constitution_gate_paths.ps1" -ForegroundColor Yellow
    if ($DryRun) {
        Write-Host "  DRY: powershell -NoProfile -ExecutionPolicy Bypass -File `"$repoRoot\scripts\verify_p0_constitution_gate_paths.ps1`""
    }
    else {
        & powershell -NoProfile -ExecutionPolicy Bypass -File "$repoRoot\scripts\verify_p0_constitution_gate_paths.ps1"
        if ($LASTEXITCODE -ne 0) { throw "verify_p0 failed (exit $LASTEXITCODE)" }
    }
}

Write-Host "[STEP] push main -> $remoteName" -ForegroundColor Yellow
if ($DryRun) {
    Write-Host "  DRY: git -C `"$mainPath`" push $remoteName main"
}
else {
    cmd /c "git -C `"$mainPath`" push $remoteName main"
    if ($LASTEXITCODE -ne 0) {
        throw "Push failed (exit $LASTEXITCODE). Fix ACL on E:\Git\repos or remote ref rules."
    }
}

Write-Host "[DONE] main on $remoteName should include $FeatureBranch." -ForegroundColor Green
Write-Host "[INFO] Optional: delete remote feature branch when finished: git push $remoteName --delete $FeatureBranch" -ForegroundColor DarkGray
