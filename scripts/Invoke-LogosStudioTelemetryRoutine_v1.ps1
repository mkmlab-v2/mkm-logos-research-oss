<#
.SYNOPSIS
  Logos Studio ECS + evidence feedback telemetry aggregation (B-track, NON_GATING).

.DESCRIPTION
  1) Optional: pull VPS no1kmedi JSONL into workspace memory/commercialization
  2) build_logos_studio_ecs_telemetry_summary_v1.py
  3) build_logos_studio_feedback_summary_v1.py

.PARAMETER IncludeVpsPull
  scp hub_events + feedback JSONL from vps-mkmlife no1kmedi app memory.

.PARAMETER Remote
  SSH host alias (default vps-mkmlife).
#>
param(
    [switch]$IncludeVpsPull,
    [string]$Remote = "vps-mkmlife",
    [string]$VpsAppRoot = "/opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$memDir = Join-Path $root "memory\commercialization"
New-Item -ItemType Directory -Force -Path $memDir | Out-Null

function Invoke-Step {
    param([string]$Name, [string[]]$Command)
    Write-Host "==> $Name"
    & $Command[0] $Command[1..($Command.Length - 1)]
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit $LASTEXITCODE"
    }
}

if ($IncludeVpsPull) {
    $remoteMem = "$VpsAppRoot/memory/commercialization"
    foreach ($file in @("hub_events.jsonl", "logos_studio_evidence_feedback_v1.jsonl")) {
        $local = Join-Path $memDir $file
        $remote = "${Remote}:${remoteMem}/${file}"
        Write-Host "==> vps_pull $file"
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & scp -o BatchMode=yes $remote $local 2>&1 | Out-Null
        $pullExit = $LASTEXITCODE
        $ErrorActionPreference = $prevEap
        if ($pullExit -ne 0) {
            Write-Host "WARN: missing remote $file (skip)" -ForegroundColor Yellow
        }
    }
}

Invoke-Step -Name "ecs_telemetry_summary" -Command @(
    "py", "scripts/build_logos_studio_ecs_telemetry_summary_v1.py"
)
Invoke-Step -Name "feedback_summary" -Command @(
    "py", "scripts/build_logos_studio_feedback_summary_v1.py"
)

$out = Join-Path $root "reports\logos_studio_telemetry_routine_latest.json"
@{
    schema    = "logos_studio_telemetry_routine_v1"
    ok        = $true
    vps_pull  = [bool]$IncludeVpsPull
    remote    = $Remote
    artifacts = @(
        "docs/final/artifacts/logos_studio_ecs_telemetry_summary_latest.json",
        "docs/final/artifacts/logos_studio_feedback_summary_latest.json"
    )
    reproduce = "powershell -File scripts/Invoke-LogosStudioTelemetryRoutine_v1.ps1"
} | ConvertTo-Json | Set-Content -Path $out -Encoding UTF8

Write-Host "WROTE: $out"
Write-Host "OK: Invoke-LogosStudioTelemetryRoutine_v1"
