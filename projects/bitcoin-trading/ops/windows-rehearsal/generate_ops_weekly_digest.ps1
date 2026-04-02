param(
    [string]$OverviewPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_health_overview_latest.json",
    [string]$ATrackPath = "C:\workspace\docs\final\artifacts\a_track_go_nogo_status_latest.json",
    [string]$OutputPath = "C:\workspace\docs\final\artifacts\OPS_WEEKLY_DIGEST_latest.md"
)

$ErrorActionPreference = "Stop"

function Read-JsonOrNull([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try { return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json } catch { return $null }
}

$ov = Read-JsonOrNull -path $OverviewPath
$at = Read-JsonOrNull -path $ATrackPath
$now = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-dd HH:mm 'UTC'")

$goNoGo = if ($null -ne $at) { [string]$at.overall_go_no_go } else { "UNKNOWN" }
$stage = if ($null -ne $at) { [string]$at.recommended_stage } else { "UNKNOWN" }
$overallOk = if ($null -ne $ov) { [string]$ov.overall_ok } else { "false" }
$degraded = if ($null -ne $ov) { [string]$ov.degraded } else { "true" }
$strictOk = if ($null -ne $ov) { [string]$ov.strict_task_schedule.overall_ok } else { "n/a" }
$opsScheduleOk = if ($null -ne $ov) { [string]$ov.ops_task_schedule.overall_ok } else { "n/a" }
$compressionOk = if ($null -ne $ov) { [string]$ov.compression_stub_health.overall_ok } else { "n/a" }
$prophecyOk = if ($null -ne $ov) { [string]$ov.prophecy_alignment_pytest.overall_ok } else { "n/a" }

if ([string]::IsNullOrWhiteSpace($goNoGo)) { $goNoGo = "UNKNOWN" }
if ([string]::IsNullOrWhiteSpace($stage)) { $stage = "UNKNOWN" }

$md = @"
# OPS Weekly Digest ($now)

## Baseline
- overall_ok: $overallOk
- degraded: $degraded
- go_no_go: $goNoGo
- recommended_stage: $stage

## Integrity Gates
- strict_task_schedule_ok: $strictOk
- ops_task_schedule_ok: $opsScheduleOk
- compression_stub_health_ok: $compressionOk
- prophecy_alignment_pytest_ok: $prophecyOk

## Event-Based Trigger Rule
- Trigger immediate report when one of below is true:
  - overall_ok=false
  - degraded=true
  - strict_task_schedule_ok=false
  - ops_task_schedule_ok=false
"@

$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
Set-Content -LiteralPath $OutputPath -Value $md -Encoding UTF8
Write-Host "WROTE: $OutputPath"
