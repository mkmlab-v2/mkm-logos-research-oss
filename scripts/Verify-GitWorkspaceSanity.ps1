<#
.SYNOPSIS
  Git / SSH 혼선 재발 방지용 빠른 점검 (로컬·VPS 공통).

.DESCRIPTION
  - .git/info/exclude 에서 tools/* / scripts/* 가 전체를 가리면서 ! 예외가 없는지 검사 (AGENTS.md 경고와 동일).
  - origin 원격, main(또는 현재 브랜치)의 upstream 존재 여부를 알림.
  - SSH Cursor 터미널 cwd 문제 시 참고: docs/final/SSH_CURSOR_JEMA12_DEPLOY_RUNBOOK.md §2.0
  - mkmlife-com VPS 작업 트리 정리(스태시 후 ff-only pull): scripts/mkmlife_vps_git_align_safe.sh
  - projects/mkm-life 디렉터리가 있으면 원퀘스천 퍼널 체인 스크립트 존재 여부를 표시. 기본은 WARN만; `-RequireMkmLifeFunnelScripts` 시 누락을 `$broken`에 반영.

.PARAMETER WorkspaceRoot
  레포 루트 (기본 C:\workspace).

.PARAMETER Strict
    위험 exclude 패턴이면 exit 1. 기본은 경고만(WARN)하고 exit 0.

.PARAMETER CheckOriginMainSync
    `git fetch origin` 후 `HEAD`와 `origin/main` 비교. 뒤처짐·앞섬·분기 시 WARN; `-Strict`이면 exit 1에 포함.

.PARAMETER RequireMkmLifeFunnelScripts
    projects/mkm-life 가 있을 때 퍼널 스크립트가 하나라도 없으면 `$broken` 처리( `-Strict` 와 함께 쓰면 exit 1 ). 기본은 WARN만.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Verify-GitWorkspaceSanity.ps1
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Verify-GitWorkspaceSanity.ps1 -Strict
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Verify-GitWorkspaceSanity.ps1 -WorkspaceRoot C:\workspace -CheckOriginMainSync -Strict
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Verify-GitWorkspaceSanity.ps1 -Strict -RequireMkmLifeFunnelScripts
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Strict,
    [switch]$CheckOriginMainSync,
    [switch]$RequireMkmLifeFunnelScripts
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

    $mkmLifeRoot = Join-Path $root "projects\mkm-life"
    if (Test-Path -LiteralPath $mkmLifeRoot -PathType Container) {
        $funnelNeed = @(
            "scripts\run-one-question-funnel-chain.mjs",
            "scripts\aggregate-one-question-funnel.mjs",
            "scripts\auto-refresh-one-question-threshold-presets.mjs",
            "scripts\derive-one-question-threshold-presets.mjs",
            "scripts\check-one-question-funnel-gate.mjs",
            "scripts\recommend-one-question-actions.mjs",
            "scripts\build-one-question-funnel-gap-report.mjs",
            "scripts\build-one-question-daily-targets.mjs",
            "scripts\build-one-question-funnel-sitrep.mjs",
            "scripts\build-one-question-funnel-weekly-report.mjs",
            "scripts\verify-one-question-funnel-operational-readiness.mjs",
            "scripts\build-one-question-ops-snapshot.mjs",
            "scripts\seed-one-question-funnel-events.mjs",
            "scripts\reset-one-question-funnel-realdata.mjs",
            "scripts\Register-OneQuestionFunnelDailyTask.ps1"
        )
        $missingFunnel = [System.Collections.Generic.List[string]]::new()
        foreach ($rel in $funnelNeed) {
            $p = Join-Path $mkmLifeRoot $rel
            if (-not (Test-Path -LiteralPath $p)) {
                [void]$missingFunnel.Add($rel)
            }
        }
        if ($missingFunnel.Count -gt 0) {
            Write-WarnLine "mkm-life one-question funnel: missing $($missingFunnel.Count) script(s): $($missingFunnel -join ', ') - npm run check:one-question:funnel-chain may fail."
            if ($RequireMkmLifeFunnelScripts) { $broken = $true }
        }
        else {
            Write-OkLine "mkm-life one-question funnel: full chain scripts present ($($funnelNeed.Count) paths)."
        }
    }

    $porcelain = git status --porcelain 2>$null
    if ($porcelain) {
        $n = ($porcelain | Measure-Object).Count
        if ($n -gt 200) {
            Write-WarnLine "Working tree has $n porcelain lines - consider commit, .gitignore, or artifact policy (noise vs intentional WIP)."
        }
    }

    if ($CheckOriginMainSync) {
        git fetch origin 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-WarnLine "git fetch origin failed - cannot verify drift vs origin/main."
            if ($Strict) { $broken = $true }
        }
        else {
            git rev-parse -q --verify refs/remotes/origin/main 2>$null | Out-Null
            if ($LASTEXITCODE -ne 0) {
                Write-WarnLine "No origin/main after fetch - check default branch name on remote."
                if ($Strict) { $broken = $true }
            }
            else {
                $behind = 0
                $ahead = 0
                $bOut = git rev-list --count HEAD..origin/main 2>$null
                if ($LASTEXITCODE -eq 0 -and $bOut -match '^\d+$') { $behind = [int]$bOut }
                $aOut = git rev-list --count origin/main..HEAD 2>$null
                if ($LASTEXITCODE -eq 0 -and $aOut -match '^\d+$') { $ahead = [int]$aOut }
                $h = git rev-parse --short HEAD 2>$null
                $r = git rev-parse --short origin/main 2>$null
                if ($behind -gt 0) {
                    Write-WarnLine "HEAD $h is $behind commit(s) BEHIND origin/main ($r) - run: git pull --ff-only origin main"
                    $broken = $true
                }
                if ($ahead -gt 0) {
                    Write-WarnLine "HEAD $h is $ahead commit(s) AHEAD of origin/main (unpushed) - push or reset before assuming VPS parity."
                    $broken = $true
                }
                if ($behind -gt 0 -and $ahead -gt 0) {
                    Write-WarnLine "DIVERGED from origin/main - do not blind pull; inspect git log."
                    $broken = $true
                }
                if ($behind -eq 0 -and $ahead -eq 0) {
                    Write-OkLine "HEAD $h matches origin/main ($r)."
                }
            }
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
