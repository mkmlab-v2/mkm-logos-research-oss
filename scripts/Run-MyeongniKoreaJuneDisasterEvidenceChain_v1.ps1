# B-track: June 2026 Korea disaster evidence chain (myeongni + weather + news lag + fusion v2).
# research_only — no Track A merge.
param(
    [string]$DateFrom = "2026-06-01",
    [string]$DateTo = "2026-06-30",
    [string]$ArchiveThrough = "2026-06-04",
    [switch]$SkipPanel,
    [switch]$SkipCorrelate
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
if (-not $SkipPanel) {
    py scripts/build_btrack_session_instant_myeongni_panel_v1.py `
        --date-from $DateFrom --date-to $DateTo `
        --hour 9 --minute 0 --iana-tz Asia/Seoul `
        --calendar-mode all `
        --out-csv reports/myeongni_korea_june2026_session_panel_v1.csv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
py scripts/build_korea_daily_weather_openmeteo_v1.py `
    --date-from $DateFrom --date-to $DateTo --archive-through $ArchiveThrough
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/build_korea_disaster_news_context_v1.py --date-from $DateFrom --date-to $DateTo --use-exa
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$fusionArgs = @(
    "scripts/build_myeongni_korea_disaster_risk_fusion_v1.py",
    "--news-csv", "reports/korea_disaster_news_context_v1.csv",
    "--skip-join"
)
if (-not $SkipCorrelate) { $fusionArgs += "--run-correlate" }
py @fusionArgs
exit $LASTEXITCODE
