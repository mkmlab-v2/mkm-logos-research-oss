param(
    [string]$TargetMarkdownPath = "C:\workspace\docs\final\artifacts\OPS_NOTEBOOK_DRIVEN_LOOP_2026-04-02_2245.md",
    [string]$OverviewPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_health_overview_latest.json"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $TargetMarkdownPath)) {
    throw "Target markdown not found: $TargetMarkdownPath"
}
if (-not (Test-Path -LiteralPath $OverviewPath)) {
    throw "Ops overview json not found: $OverviewPath"
}

$o = Get-Content -LiteralPath $OverviewPath -Raw -Encoding UTF8 | ConvertFrom-Json
$stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

$block = @(
    "",
    "## Auto Snapshot ($stamp)",
    "",
    "- schema: ``$($o.schema)``",
    "- overall_ok: ``$($o.overall_ok)``",
    "- degraded: ``$($o.degraded)``",
    "- strict_task_schedule.ok: ``$($o.strict_task_schedule.overall_ok)``",
    "- ops_task_schedule.ok: ``$($o.ops_task_schedule.overall_ok)``",
    "- compression_stub_health.ok: ``$($o.compression_stub_health.overall_ok)``",
    "- prophecy_alignment_pytest.ok: ``$($o.prophecy_alignment_pytest.overall_ok)``"
)

Add-Content -LiteralPath $TargetMarkdownPath -Value ($block -join [Environment]::NewLine) -Encoding UTF8
Write-Host "Appended ops snapshot to: $TargetMarkdownPath"
