<#
.SYNOPSIS
  Git / SSH 혼선 재발 방지용 빠른 점검 (로컬·VPS 공통).

.DESCRIPTION
  - .git/info/exclude 에서 tools/* / scripts/* 가 전체를 가리면서 ! 예외가 없는지 검사 (AGENTS.md 경고와 동일).
  - origin 원격, main(또는 현재 브랜치)의 upstream 존재 여부를 알림.
  - SSH Cursor 터미널 cwd 문제 시 참고: docs/final/SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md §2.0

.PARAMETER WorkspaceRoot
  레포 루트 (기본 C:\workspace).

.PARAMETER Strict
  위험 exclude 패턴이면 exit 1. 기본은 경고만(WARN)하고 exit 0.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Verify-GitWorkspaceSanity.ps1
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Verify-GitWorkspaceSanity.ps1 -Strict
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot
$excludePath = Join-Path $root ".git\info\exclude"
$broken = $false

function Write-WarnLine([string]$msg) {
    Write-Host "WARN: $msg" -ForegroundColor Yellow
}

function Write-OkLine([string]$msg) {
    Write-Host "OK: $msg" -ForegroundColor Green
}

function Test-Unignore([string[]]$L, [string]$Prefix) {
    foreach ($x in $L) {
        if ($x -like "!${Prefix}*") { return $true }
    }
    return $false
}

if (-not (Test-Path -LiteralPath (Join-Path $root ".git"))) {
    Write-WarnLine "Not a git repository at $root - skip."
    exit 0
}

# --- .git/info/exclude: broad tools/scripts suppression without un-ignore ---
if (Test-Path -LiteralPath $excludePath) {
    $raw = Get-Content -LiteralPath $excludePath -ErrorAction Stop
    $lines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in $raw) {
        $t = $line.Trim()
        if ($t -match '^\s*#' -or $t -eq '') { continue }
        [void]$lines.Add($t)
    }
    $arr = $lines.ToArray()

    $hasToolsStar = $arr -contains 'tools/*'
    $hasScriptsStar = $arr -contains 'scripts/*'
    if ($hasToolsStar -and -not (Test-Unignore $arr 'tools/')) {
        Write-WarnLine ".git/info/exclude: 'tools/*' without '!tools/...' - tracked tools may be hidden (AGENTS.md Git exclude note)."
        $broken = $true
    }
    if ($hasScriptsStar -and -not (Test-Unignore $arr 'scripts/')) {
        Write-WarnLine ".git/info/exclude: 'scripts/*' without '!scripts/...' - tracked scripts may be hidden."
        $broken = $true
    }
    foreach ($pat in @('tools/', 'scripts/')) {
        if ($arr -contains $pat) {
            Write-WarnLine ".git/info/exclude: bare '$pat' - hides entire tree; use 'path/*' + '!path/keep/**' (AGENTS.md)."
            $broken = $true
        }
    }
    if (-not $broken) {
        Write-OkLine ".git/info/exclude: tools/* and scripts/* paired with ! un-ignore patterns."
    }
}
else {
    Write-OkLine ".git/info/exclude not present (optional)."
}

# --- remotes / upstream (informational) ---
Push-Location $root
try {
    $origin = git remote get-url origin 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($origin)) {
        Write-WarnLine "Git remote 'origin' missing - push/pull sync will fail."
        if ($Strict) { $broken = $true }
    }
    else {
        Write-OkLine "origin = $origin"
    }

    $branch = git rev-parse --abbrev-ref HEAD 2>$null
    if ($branch) {
        git rev-parse "@{upstream}" 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-WarnLine "Branch '$branch' has no upstream - set with: git branch --set-upstream-to=origin/$branch"
        }
        else {
            $up = git rev-parse --abbrev-ref "@{upstream}" 2>$null
            Write-OkLine "upstream = $up"
        }
    }

    $porcelain = git status --porcelain 2>$null
    if ($porcelain) {
        $n = ($porcelain | Measure-Object).Count
        if ($n -gt 200) {
            Write-WarnLine "Working tree has $n porcelain lines - consider commit, .gitignore, or artifact policy (noise vs intentional WIP)."
        }
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Ref: docs/final/SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md (SSH cwd, git pull, nginx)." -ForegroundColor DarkGray
Write-Host "Ref: AGENTS.md (SSH Cursor, git sync, .git/info/exclude warning)." -ForegroundColor DarkGray

if ($broken) {
    if ($Strict) {
        Write-Host "FAIL: Git workspace sanity (Strict)." -ForegroundColor Red
        exit 1
    }
    Write-Host "WARN: issues above - fix before VPS/GitHub sync surprises." -ForegroundColor Yellow
}
exit 0
