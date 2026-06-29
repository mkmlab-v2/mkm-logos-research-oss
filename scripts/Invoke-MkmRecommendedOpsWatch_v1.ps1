<#
.SYNOPSIS
  Recommended ops watch bundle: KOSPI email passive + Cursor Origin + session guard + GeekNews.

.DESCRIPTION
  Observation-only — no auto policy changes. GeekNews/Cursor fetch failures are non-fatal.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipGeekNews,
    [switch]$SkipCursorOrigin,
    [switch]$SkipSessionGuard,
    [switch]$SkipKospiPassive,
    [switch]$ForceKospiPassive
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$steps = [ordered]@{}
$fatalOk = $true

function Invoke-WatchStep {
    param(
        [string]$Name,
        [scriptblock]$Block,
        [switch]$NonFatal
    )
    & $Block
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    $steps[$Name] = @{ exit_code = $code; non_fatal = [bool]$NonFatal }
    if ($code -ne 0 -and -not $NonFatal) { $script:fatalOk = $false }
    return $code
}

if (-not $SkipKospiPassive) {
    $kospiArgs = @("scripts\check_kospi_morning_email_digest_passive_v1.py")
    if ($ForceKospiPassive) { $kospiArgs += "--force" }
    Invoke-WatchStep "kospi_morning_passive" {
        py @kospiArgs
    } | Out-Null
}

if (-not $SkipCursorOrigin) {
    Invoke-WatchStep "cursor_origin_watch" {
        py scripts\check_cursor_origin_watch_v1.py
    } -NonFatal | Out-Null
}

if (-not $SkipSessionGuard) {
    Invoke-WatchStep "agent_session_guard" {
        py scripts\check_agent_session_guard_v1.py
    } -NonFatal | Out-Null
}

if (-not $SkipGeekNews) {
    Invoke-WatchStep "geeknews_watch" {
        py scripts\fetch_geeknews_watch_v1.py
    } -NonFatal | Out-Null
}

$report = [ordered]@{
    schema = "mkm_recommended_ops_watch_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")
    ok = $fatalOk
    steps = $steps
    operator_note_ko = "권장 3종+GeekNews 관찰 — Telegram/정책 자동 변경 없음"
}

$outPath = Join-Path $WorkspaceRoot "reports\mkm_recommended_ops_watch_latest.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($outPath, (($report | ConvertTo-Json -Depth 6) + "`n"), $utf8NoBom)
Write-Host "WROTE: $outPath"
Write-Host "RECOMMENDED_OPS_WATCH_OK=$fatalOk"

if (-not $fatalOk) { exit 1 }
exit 0
