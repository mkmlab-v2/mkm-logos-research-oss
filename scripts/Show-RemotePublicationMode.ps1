#Requires -Version 5.1
<#
.SYNOPSIS
  Show current Git remote publication mode (internal-first / GitHub blocked).

.DESCRIPTION
  Prints fetch/push URLs for all remotes and highlights whether GitHub push URLs
  are blocked via "no_push". This is a read-only guardrail check.
#>

$ErrorActionPreference = "Stop"

Set-Location "C:\workspace"

$lines = git remote -v
if ($LASTEXITCODE -ne 0) {
    throw "git remote -v failed."
}

Write-Host "== Remote publication mode =="
$lines | ForEach-Object { Write-Host $_ }
Write-Host ""

$githubPushBlocked = $true
$githubPushAllowed = @()

$lines | ForEach-Object {
    $line = $_.Trim()
    if ($line -match "^(?<name>\S+)\s+(?<url>\S+)\s+\((?<kind>fetch|push)\)$") {
        $name = $matches["name"]
        $url = $matches["url"]
        $kind = $matches["kind"]
        if ($kind -eq "push" -and $line -match "github\.com") {
            $githubPushBlocked = $false
            $githubPushAllowed += "$name -> $url"
        }
        if ($kind -eq "push" -and $url -eq "no_push") {
            # expected for blocked GitHub remotes
            return
        }
    }
}

if ($githubPushBlocked) {
    Write-Host "[OK] GitHub push URLs are blocked (no_push)." -ForegroundColor Green
} else {
    Write-Host "[WARN] Some GitHub push URLs are enabled:" -ForegroundColor Yellow
    $githubPushAllowed | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
}

Write-Host "[INFO] Internal-first push command: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/push-internal.ps1"
