#Requires -Version 5.1
<#
.SYNOPSIS
  Tier3 human paste helper — correction comments for Reddit + X (clipboard + open targets).

.EXAMPLE
  powershell -File scripts/Invoke-UniversalRootCorrectionPasteTier3_v1.ps1 -Channel Reddit
  powershell -File scripts/Invoke-UniversalRootCorrectionPasteTier3_v1.ps1 -Channel X
  powershell -File scripts/Invoke-UniversalRootCorrectionPasteTier3_v1.ps1 -Channel All
#>
param(
    [ValidateSet('Reddit', 'X', 'All')]
    [string]$Channel = 'All',

    [switch]$SkipBrowser
)

$ErrorActionPreference = 'Stop'
$Root = 'C:\workspace'
Set-Location $Root

$RedditPaste = Join-Path $Root 'reports/human_paste/universal_root_reddit_public_correction_v1.md'
$XPaste = Join-Path $Root 'reports/human_paste/universal_root_x_public_correction_v1.txt'
$GifLocal = Join-Path $Root 'reports/commercial/logos_observatory_product_demo_10s.gif'
$GifGitHub = 'https://github.com/mkmlab-v2/mkm-universal-root/blob/main/docs/assets/logos_observatory_product_demo_10s.gif'
$XReplyUrl = 'https://x.com/moksorinw/status/2068734802661175789'

function Invoke-RedditStep {
    if (-not (Test-Path -LiteralPath $RedditPaste)) { throw "Missing $RedditPaste" }
    $text = Get-Content -LiteralPath $RedditPaste -Raw -Encoding UTF8
    Set-Clipboard -Value $text.TrimEnd()
    Write-Host '[UR-GTM] Reddit correction copied to clipboard.' -ForegroundColor Green
    Write-Host "GIF link: $GifGitHub"
    if (-not $SkipBrowser) {
        Start-Process 'https://www.reddit.com/r/LocalLLM/search/?q=Research%20PoC%20MIT%20fixture&restrict_sr=1'
        Start-Process 'https://www.reddit.com/user/me/submitted/'
        Write-Host '[UR-GTM] Opened r/LocalLLM search + your submitted posts. Pick original thread → Comment (Ctrl+V).' -ForegroundColor Yellow
    }
}

function Invoke-XStep {
    if (-not (Test-Path -LiteralPath $XPaste)) { throw "Missing $XPaste" }
    $text = Get-Content -LiteralPath $XPaste -Raw -Encoding UTF8
    Set-Clipboard -Value $text.TrimEnd()
    Write-Host '[UR-GTM] X correction copied to clipboard.' -ForegroundColor Green
    if (Test-Path -LiteralPath $GifLocal) {
        Write-Host "[UR-GTM] Optional GIF attach: $GifLocal" -ForegroundColor Cyan
        if (-not $SkipBrowser) { Start-Process -FilePath $GifLocal }
    }
    if (-not $SkipBrowser) {
        Start-Process $XReplyUrl
        Write-Host '[UR-GTM] Reply on X (Ctrl+V); attach GIF if desired.' -ForegroundColor Yellow
    }
}

switch ($Channel) {
    'Reddit' { Invoke-RedditStep }
    'X'      { Invoke-XStep }
    'All'    {
        Invoke-RedditStep
        if (-not $SkipBrowser) { Read-Host 'Press Enter when Reddit comment is posted (X step next)' }
        Invoke-XStep
    }
}

Write-Host '[UR-GTM] After paste: py scripts/poll_universal_root_community_gtm_v1.py' -ForegroundColor Cyan
