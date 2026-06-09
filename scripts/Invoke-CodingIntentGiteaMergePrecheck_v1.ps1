# Gitea/internal merge precheck — coding intent manifest + link verify (research_only).
# Internal-first publication; GitHub PR is not SSOT.
param(
    [string]$IntegrationRemote = "gitea",
    [switch]$SkipFetch,
    [switch]$RecordLink,
    [switch]$Strict,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

function Resolve-IntegrationRemote {
    param([string]$Preferred)
    $remotes = @(git remote)
    if ($remotes -contains $Preferred) { return $Preferred }
    if ($Preferred -eq "gitea" -and $remotes -contains "internal") {
        Write-Host "[INFO] Using internal (gitea missing)." -ForegroundColor DarkCyan
        return "internal"
    }
    if ($remotes -contains "internal") { return "internal" }
    throw "Neither gitea nor internal remote found."
}

$remote = Resolve-IntegrationRemote -Preferred $IntegrationRemote
$base = "$remote/main"

if (-not $SkipFetch) {
    Write-Host "== fetch $remote ==" -ForegroundColor Cyan
    if (-not $DryRun) {
        git fetch $remote --quiet 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "git fetch $remote failed; continuing with local refs."
        }
    }
}

if ($RecordLink) {
    Write-Host "== record coding intent link ==" -ForegroundColor Cyan
    $recArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $PSScriptRoot "Invoke-CodingIntentLinkRecord_v1.ps1"),
        "-IncludeDiff", "-RunGate", "-AllowPartial"
    )
    if ($DryRun) {
        Write-Host "WhatIf: pwsh $($recArgs -join ' ')"
    } else {
        powershell @recArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

Write-Host "== PR manifest ($base..HEAD) ==" -ForegroundColor Cyan
$manifestArgs = @((Join-Path $PSScriptRoot "build_coding_intent_pr_manifest_v1.py"), "--base", $base)
if ($DryRun) {
    Write-Host "WhatIf: py $($manifestArgs -join ' ')"
} else {
    & py @manifestArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "== gitea merge precheck summary ==" -ForegroundColor Cyan
$precheckArgs = @(
    (Join-Path $PSScriptRoot "build_coding_intent_gitea_merge_precheck_v1.py"),
    "--integration-remote", $remote
)
if ($Strict) { $precheckArgs += "--strict" }
if ($DryRun) {
    $precheckArgs += "--dry-run"
    & py @precheckArgs
    exit $LASTEXITCODE
}

& py @precheckArgs
$code = $LASTEXITCODE
if ($code -eq 2 -and -not $Strict) { $code = 0 }
exit $code
