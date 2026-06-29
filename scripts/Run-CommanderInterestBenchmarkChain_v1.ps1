param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipTelegram,
    [switch]$DryRunTelegram,
    [switch]$SkipIngest,
    [switch]$IncludeRss,
    [switch]$IncludePodcastTts
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$steps = [ordered]@{}
$ok = $true

function Invoke-ChainStep {
    param(
        [string]$Name,
        [string]$ScriptRelPath,
        [string[]]$ExtraArgs = @()
    )
    Write-Host "[STEP] $Name"
    $scriptPath = Join-Path $WorkspaceRoot $ScriptRelPath
    if ($ExtraArgs.Count -gt 0) {
        & py -3 $scriptPath @ExtraArgs
    } else {
        & py -3 $scriptPath
    }
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    $steps[$Name] = @{ exit_code = $code }
    if ($code -ne 0) { $script:ok = $false }
    return $code
}

if (-not $SkipIngest) {
    Invoke-ChainStep "signal_log_prune" "scripts\prune_commander_interest_signal_log_v1.py" | Out-Null
    if (-not $ok) { exit 1 }
    Invoke-ChainStep "inbox_ingest" "scripts\ingest_commander_interest_signal_inbox_v1.py" | Out-Null
    if (-not $ok) { exit 1 }
}

if ($IncludeRss) {
    Invoke-ChainStep "rss_collect" "scripts\collect_commander_interest_signals_rss_v1.py" | Out-Null
    if (-not $ok) { exit 1 }
}

Invoke-ChainStep "weekly_benchmark_report" "scripts\build_commander_interest_benchmark_weekly_report_v1.py" | Out-Null
if (-not $ok) { exit 1 }

Invoke-ChainStep "ai_native_briefing_pack" "scripts\build_commander_ai_native_briefing_pack_v1.py" | Out-Null
if (-not $ok) { exit 1 }

Invoke-ChainStep "clinic_health_newsletter_draft" "scripts\build_clinic_member_health_newsletter_draft_v1.py" | Out-Null
if (-not $ok) { exit 1 }

if (-not $SkipTelegram) {
    $tgExtra = @()
    if ($DryRunTelegram) { $tgExtra = @("--dry-run") }
    Invoke-ChainStep "telegram_digest" "scripts\send_commander_interest_benchmark_telegram_v1.py" -ExtraArgs $tgExtra | Out-Null
    if (-not $ok) { exit 1 }
    Invoke-ChainStep "telegram_health_newsletter" "scripts\send_clinic_member_health_newsletter_telegram_v1.py" -ExtraArgs $tgExtra | Out-Null
}

if ($IncludePodcastTts) {
    Invoke-ChainStep "podcast_tts" "scripts\render_commander_ai_native_podcast_tts_v1.py" | Out-Null
}

$out = [ordered]@{
    schema = "commander_interest_benchmark_chain_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    ok = $ok
    steps = $steps
    artifacts = [ordered]@{
        weekly_json = "docs/final/artifacts/commander_interest_benchmark_weekly_latest.json"
        weekly_md = "docs/final/artifacts/commander_interest_benchmark_weekly_latest.md"
        briefing_pack_json = "docs/final/artifacts/commander_ai_native_briefing_pack_latest.json"
        briefing_md = "docs/final/artifacts/commander_ai_native_briefing_latest.md"
        card_news_md = "docs/final/artifacts/commander_ai_native_card_news_latest.md"
        podcast_script_md = "docs/final/artifacts/commander_ai_native_podcast_script_latest.md"
        health_newsletter_md = "docs/final/artifacts/clinic_member_health_newsletter_draft_latest.md"
        health_newsletter_json = "docs/final/artifacts/clinic_member_health_newsletter_draft_latest.json"
    }
}

$reportDir = Join-Path $WorkspaceRoot "reports"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$latestPath = Join-Path $reportDir "commander_interest_benchmark_chain_latest.json"
$out | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $latestPath -Encoding UTF8

Write-Host "[DONE] commander interest benchmark chain ok=$ok" -ForegroundColor $(if ($ok) { "Green" } else { "Red" })
Write-Host "  weekly: docs/final/artifacts/commander_interest_benchmark_weekly_latest.json"
Write-Host "  briefing: docs/final/artifacts/commander_ai_native_briefing_pack_latest.json"
Write-Host "  sop: docs/final/artifacts/commander_interest_daily_sop_v1.md"

if (-not $ok) { exit 1 }
exit 0
