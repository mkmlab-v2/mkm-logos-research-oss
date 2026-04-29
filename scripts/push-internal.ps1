#Requires -Version 5.1
param(
    [switch]$SetUpstream
)

$ErrorActionPreference = "Stop"

$repoRoot = "C:\workspace"
Set-Location $repoRoot

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if (-not $branch) {
    throw "Could not determine current branch."
}

$remoteUrl = (git remote get-url internal 2>$null).Trim()
if (-not $remoteUrl) {
    throw "Remote 'internal' is not configured. Run Setup-InternalGitRemote-E.ps1 first."
}

Write-Host "[INFO] Repo:   $repoRoot" -ForegroundColor Cyan
Write-Host "[INFO] Branch: $branch" -ForegroundColor Cyan
Write-Host "[INFO] Push -> internal ($remoteUrl)" -ForegroundColor Cyan

function Set-UpstreamIfRequested {
    param(
        [string]$BranchName
    )
    if (-not $SetUpstream) { return }
    git branch --set-upstream-to "internal/$BranchName" $BranchName | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[INFO] Upstream set: internal/$BranchName" -ForegroundColor DarkCyan
    }
}

$localSha = (git rev-parse HEAD).Trim()
$remoteLine = (git ls-remote --heads internal "refs/heads/$branch").Trim()
$remoteSha = $null
if ($remoteLine) {
    $remoteSha = ($remoteLine -split "\s+")[0]
}

if ($remoteSha -and $remoteSha -eq $localSha) {
    Set-UpstreamIfRequested -BranchName $branch
    Write-Host "[DONE] Internal already up-to-date (same commit)." -ForegroundColor Green
    exit 0
}

$pushOutput = if ($SetUpstream) {
    git push -u internal HEAD 2>&1
} else {
    git push internal HEAD 2>&1
}
$pushText = ($pushOutput | Out-String)

if ($LASTEXITCODE -ne 0) {
    if ($pushText -match "reference already exists") {
        $remoteLineAfter = (git ls-remote --heads internal "refs/heads/$branch").Trim()
        $remoteShaAfter = if ($remoteLineAfter) { ($remoteLineAfter -split "\s+")[0] } else { $null }
        if ($remoteShaAfter -and $remoteShaAfter -eq $localSha) {
            Set-UpstreamIfRequested -BranchName $branch
            Write-Host "[DONE] Internal already had the same branch ref." -ForegroundColor Green
            exit 0
        }
        throw "Push rejected: branch ref exists with different state. Inspect internal/$branch and resolve divergence."
    }
    if ($pushText -match "unable to create temporary object directory|remote unpack failed|Permission denied|unpacker error") {
        throw "Push to internal failed due to remote write/unpack permissions. Check ACL/ownership on E:\\Git\\repos."
    }
    throw "Push to internal failed (exit code: $LASTEXITCODE). Details: $pushText"
}

Write-Host "[DONE] Pushed to internal only." -ForegroundColor Green
