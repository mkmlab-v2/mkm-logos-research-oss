<#
.SYNOPSIS
  GitHub 원격(origin/hq 등)에 대한 실수 푸시를 막기 위해 push URL만 비활성화한다.
  fetch/pull은 기존 URL 그대로 유지된다. 본선 푸시는 internal 등 비-GitHub 원격을 사용한다.

.PARAMETER Restore
  각 원격의 push URL을 fetch URL과 동일하게 되돌린다(GitHub 푸시 재허용).

.EXAMPLE
  pwsh -NoProfile -File scripts/Git-DisableGitHubPushUrls.ps1
  pwsh -NoProfile -File scripts/Git-DisableGitHubPushUrls.ps1 -Restore
#>
param(
    [switch]$Restore
)

$ErrorActionPreference = 'Stop'

function Get-GitRemotes {
    $lines = git remote 2>$null
    if ($LASTEXITCODE -ne 0) { throw "git remote failed" }
    return @($lines | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

foreach ($name in (Get-GitRemotes)) {
    $fetchUrl = (git remote get-url $name 2>$null).Trim()
    if ([string]::IsNullOrWhiteSpace($fetchUrl)) { continue }
    if ($fetchUrl -notmatch 'github\.com') { continue }

    if ($Restore) {
        git remote set-url --push $name $fetchUrl
        Write-Host "Restored push URL for $name -> (same as fetch)"
        continue
    }

    # Sentinel: push 시 즉시 실패; 네트워크로 비밀이 나가지 않음.
    git remote set-url --push $name "no_push"
    Write-Host "Disabled push for GitHub remote '$name' (fetch unchanged): $fetchUrl"
}

Write-Host "Done. Verify: git remote -v"
