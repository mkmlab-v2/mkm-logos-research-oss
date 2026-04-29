param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-PreNews-Shadow-Daily"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts/check_pre_news_shadow_task_health.ps1" `
    -WorkspaceRoot $WorkspaceRoot `
    -TaskName $TaskName
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py -3 "scripts/alert_pre_news_shadow_task_health_v1.py" `
    --health-json "docs/final/artifacts/pre_news_shadow_task_health_latest.json" `
    --out-alert-json "docs/final/artifacts/pre_news_shadow_task_health_alert_latest.json" `
    --append-log-jsonl "reports/pre_news_shadow_task_health_alert_log.jsonl"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DONE: pre-news shadow health chain." -ForegroundColor Green

