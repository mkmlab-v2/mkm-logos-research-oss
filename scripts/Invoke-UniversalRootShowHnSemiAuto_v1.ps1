#Requires -Version 5.1
<#
.SYNOPSIS
  Tier 3 Show HN semi-auto — pre-gate checklist, clipboard steps, open submit (commander clicks Submit).

.EXAMPLE
  powershell -File scripts\Invoke-UniversalRootShowHnSemiAuto_v1.ps1
  powershell -File scripts\Invoke-UniversalRootShowHnSemiAuto_v1.ps1 -SkipBrowser
  powershell -File scripts\Invoke-UniversalRootShowHnSemiAuto_v1.ps1 -SkipPreGate
#>
param(
    [switch]$SkipBrowser,
    [switch]$SkipPreGate,
    [switch]$NonInteractive
)

$ErrorActionPreference = 'Stop'
$Root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { 'C:\workspace' }
Set-Location $Root

$PasteDir = Join-Path $Root 'reports/human_paste'
$TitlePath = Join-Path $PasteDir 'universal_root_show_hn_title.txt'
$BodyPath = Join-Path $PasteDir 'universal_root_show_hn_body.md'
$CommentPath = Join-Path $PasteDir 'universal_root_show_hn_first_comment.md'
$SubmitUrl = 'https://news.ycombinator.com/submit'
$RepoUrl = 'https://github.com/mkmlab-v2/mkm-universal-root'
$ChecklistScript = Join-Path $Root 'scripts/build_universal_root_show_hn_launch_checklist_v1.py'
$RecordScript = Join-Path $Root 'scripts/record_universal_root_show_hn_post_v1.py'

function Wait-Step([string]$Prompt) {
    if ($NonInteractive) { return }
    Read-Host $Prompt
}

function Set-Clip([string]$Text, [string]$Label) {
    Set-Clipboard -Value $Text.TrimEnd()
    Write-Host "[UR-HN] $Label copied ($($Text.TrimEnd().Length) chars)." -ForegroundColor Green
}

if (-not $SkipPreGate) {
    Write-Host '[UR-HN] Running pre-submit checklist...' -ForegroundColor Cyan
    & py $ChecklistScript
    if ($LASTEXITCODE -ne 0) {
        throw "Pre-submit checklist failed (exit $LASTEXITCODE). Fix violations before Show HN."
    }
}

foreach ($p in @($TitlePath, $BodyPath, $CommentPath)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Missing paste: $p" }
}

$title = (Get-Content -LiteralPath $TitlePath -Raw -Encoding UTF8).TrimEnd()
$body = (Get-Content -LiteralPath $BodyPath -Raw -Encoding UTF8).TrimEnd()
$comment = (Get-Content -LiteralPath $CommentPath -Raw -Encoding UTF8).TrimEnd()

Write-Host '[UR-HN] Show HN semi-auto (Tier 3). You must click Submit and post first comment.' -ForegroundColor Yellow
Write-Host "[UR-HN] Profile email must be set on news.ycombinator.com/user?id=moksorinw" -ForegroundColor Yellow

if (-not $SkipBrowser) {
    Start-Process $SubmitUrl
    Write-Host "[UR-HN] Opened $SubmitUrl" -ForegroundColor Cyan
}

Wait-Step 'Step 1/4: Submit page open. Press Enter to copy TITLE to clipboard'
Set-Clip $title 'Title'
Write-Host $title

Wait-Step 'Step 2/4: Paste title in form. Press Enter to copy URL to clipboard'
Set-Clip $RepoUrl 'URL'
Write-Host $RepoUrl

Wait-Step 'Step 3/4: Paste URL in form. Press Enter to copy BODY text to clipboard'
Set-Clip $body 'Body'
Write-Host $body

Wait-Step 'Step 4/4: Paste body, click Submit on HN. Press Enter when thread is live (copy first comment next)'
Set-Clip $comment 'First comment'
Write-Host $comment
Write-Host '[UR-HN] Paste first comment on your new thread immediately.' -ForegroundColor Yellow

if (-not $NonInteractive) {
    $hnUrl = Read-Host 'Paste Show HN thread URL here (or Enter to skip record)'
    if ($hnUrl -and $hnUrl.Trim()) {
        & py $RecordScript --url $hnUrl.Trim()
        if ($LASTEXITCODE -ne 0) { Write-Warning "Record script exit $LASTEXITCODE" }
    }
}

Write-Host '[UR-HN] Done. Optional: py scripts/poll_universal_root_community_gtm_v1.py' -ForegroundColor Cyan
