param(
    [string]$TargetMarkdownPath = "C:\workspace\docs\final\artifacts\OPS_NOTEBOOK_DRIVEN_LOOP_2026-04-02_2245.md",
    [string]$OverviewPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_health_overview_latest.json",
    [string]$BaselinePath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_health_overview_delta_baseline.json"
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

function Get-KeyMap([object]$x) {
    return [ordered]@{
        "overall_ok" = [string]$x.overall_ok
        "degraded" = [string]$x.degraded
        "strict_task_schedule.ok" = [string]$x.strict_task_schedule.overall_ok
        "ops_task_schedule.ok" = [string]$x.ops_task_schedule.overall_ok
        "compression_stub_health.ok" = [string]$x.compression_stub_health.overall_ok
        "prophecy_alignment_pytest.ok" = [string]$x.prophecy_alignment_pytest.overall_ok
        "jemaai_e2e_alert.ok" = [string]$x.jemaai_e2e_alert.overall_ok
        "blind_replay_multi_seed.ok" = [string]$x.blind_replay_multi_seed.overall_ok
    }
}

$curr = Get-KeyMap -x $o
$prev = $null
if (Test-Path -LiteralPath $BaselinePath) {
    try {
        $prevObj = Get-Content -LiteralPath $BaselinePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $prev = Get-KeyMap -x $prevObj
    } catch {
        $prev = $null
    }
}

$delta = @()
foreach ($k in $curr.Keys) {
    $before = if ($null -ne $prev -and $prev.Contains($k)) { [string]$prev[$k] } else { "<unset>" }
    $after = [string]$curr[$k]
    if ($before -ne $after) {
        $delta += "- ``$k``: ``$before`` -> ``$after``"
    }
}

if ($delta.Count -gt 0) {
    $block = @(
        "",
        "## Auto Delta Snapshot ($stamp)",
        "",
        "- schema: ``$($o.schema)``",
        "- checked_at_utc: ``$($o.checked_at_utc)``",
        "- changed: ``$($delta.Count)``",
        ""
    ) + $delta
    Add-Content -LiteralPath $TargetMarkdownPath -Value ($block -join [Environment]::NewLine) -Encoding UTF8
    Write-Host "Appended delta snapshot to: $TargetMarkdownPath (changed=$($delta.Count))"
} else {
    Write-Host "No ops delta detected; markdown append skipped."
}

$baselineParent = Split-Path -Parent $BaselinePath
if ($baselineParent -and -not (Test-Path -LiteralPath $baselineParent)) {
    New-Item -ItemType Directory -Path $baselineParent -Force | Out-Null
}
$o | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $BaselinePath -Encoding UTF8
