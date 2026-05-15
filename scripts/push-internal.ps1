#Requires -Version 5.1
param(
    [switch]$SetUpstream,
    # When false (default), after a successful push (or already-up-to-date), run
    # scripts/Invoke-GiteaRedundantDevBranchPrune_v1.ps1 if remote "gitea" exists.
    [switch]$NoAutoPruneRedundantDev
)

$ErrorActionPreference = "Stop"
# In newer PowerShell, native stderr can be promoted to ErrorRecord.
# Keep git stderr as output text so push banners don't look like failures.
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$repoRoot = "C:\workspace"
Set-Location $repoRoot

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if (-not $branch) {
    throw "Could not determine current branch."
}

$remoteName = $null
$remoteUrl = $null
foreach ($candidate in @("internal", "gitea")) {
    $candidateUrl = (git remote get-url $candidate 2>$null).Trim()
    if ($candidateUrl) {
        $remoteName = $candidate
        $remoteUrl = $candidateUrl
        break
    }
}
if (-not $remoteName) {
    throw "No internal publish remote found. Expected one of: internal, gitea."
}

Write-Host "[INFO] Repo:   $repoRoot" -ForegroundColor Cyan
Write-Host "[INFO] Branch: $branch" -ForegroundColor Cyan
Write-Host "[INFO] Push -> $remoteName ($remoteUrl)" -ForegroundColor Cyan

function Invoke-PostPushGiteaRedundantDevPrune {
    if ($NoAutoPruneRedundantDev) { return }
    $pruneScript = Join-Path $PSScriptRoot "Invoke-GiteaRedundantDevBranchPrune_v1.ps1"
    if (-not (Test-Path $pruneScript)) { return }
    try {
        & $pruneScript
    } catch {
        Write-Warning "Post-push redundant dev prune skipped: $($_.Exception.Message)"
    }
}

function Set-UpstreamIfRequested {
    param(
        [string]$BranchName,
        [string]$RemoteName
    )
    if (-not $SetUpstream) { return }
    git branch --set-upstream-to "$RemoteName/$BranchName" $BranchName | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[INFO] Upstream set: $RemoteName/$BranchName" -ForegroundColor DarkCyan
    }
}

$localSha = (git rev-parse HEAD).Trim()
$remoteOut = @(git ls-remote --heads $remoteName "refs/heads/$branch" 2>$null)
$remoteLine = if ($remoteOut.Count -gt 0) { $remoteOut[0].ToString().Trim() } else { "" }
$remoteSha = $null
if ($remoteLine) {
    $remoteSha = ($remoteLine -split "\s+")[0]
}

if ($remoteSha -and $remoteSha -eq $localSha) {
    Set-UpstreamIfRequested -BranchName $branch -RemoteName $remoteName
    Write-Host "[DONE] $remoteName already up-to-date (same commit)." -ForegroundColor Green
    Invoke-PostPushGiteaRedundantDevPrune
    exit 0
}

function Invoke-GitPushText {
    param(
        [string]$RemoteName,
        [bool]$UseUpstream
    )
    $args = if ($UseUpstream) { "push -u $RemoteName HEAD 2>&1" } else { "push $RemoteName HEAD 2>&1" }
    # Run through cmd so stderr is captured as plain text and does not surface as PowerShell ErrorRecord noise.
    $text = (& cmd /c "git $args" | Out-String)
    return $text
}

$pushText = Invoke-GitPushText -RemoteName $remoteName -UseUpstream:$SetUpstream

if ($LASTEXITCODE -ne 0) {
    if ($pushText -match "reference already exists") {
        $rlaOut = @(git ls-remote --heads $remoteName "refs/heads/$branch" 2>$null)
        $remoteLineAfter = if ($rlaOut.Count -gt 0) { $rlaOut[0].ToString().Trim() } else { "" }
        $remoteShaAfter = if ($remoteLineAfter) { ($remoteLineAfter -split "\s+")[0] } else { $null }
        if ($remoteShaAfter -and $remoteShaAfter -eq $localSha) {
            Set-UpstreamIfRequested -BranchName $branch -RemoteName $remoteName
            Write-Host "[DONE] $remoteName already had the same branch ref." -ForegroundColor Green
            Invoke-PostPushGiteaRedundantDevPrune
            exit 0
        }
        throw "Push rejected: branch ref exists with different state. Inspect $remoteName/$branch and resolve divergence."
    }
    if ($pushText -match "unable to create temporary object directory|remote unpack failed|Permission denied|unpacker error") {
        throw "Push to $remoteName failed due to remote write/unpack permissions. Check ACL/ownership on E:\\Git\\repos."
    }
    throw "Push to $remoteName failed (exit code: $LASTEXITCODE). Details: $pushText"
}

Write-Host "[DONE] Pushed to $remoteName only." -ForegroundColor Green
Invoke-PostPushGiteaRedundantDevPrune
