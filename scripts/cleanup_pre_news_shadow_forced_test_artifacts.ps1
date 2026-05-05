param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$targets = @(
    "docs/final/artifacts/pre_news_shadow_task_health_forced_unhealthy.json",
    "docs/final/artifacts/pre_news_shadow_task_health_alert_forced_test.json",
    "reports/pre_news_shadow_task_health_alert_forced_test_log.jsonl"
)

foreach ($rel in $targets) {
    $path = Join-Path $WorkspaceRoot $rel
    if (Test-Path -LiteralPath $path) {
        if ($DryRun) {
            Write-Host "[DryRun] Would remove: $path"
        }
        else {
            Remove-Item -LiteralPath $path -Force
            Write-Host "Removed: $path"
        }
    }
}

Write-Host "DONE: cleanup_pre_news_shadow_forced_test_artifacts"

