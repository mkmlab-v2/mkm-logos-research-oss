#Requires -Version 5.1
<#
.SYNOPSIS
  Charter R4 — monthly KOSPI lens ablation walk-forward refresh (B-track [HYPO]).

.DESCRIPTION
  Wrapper for scripts/run_kospi_lens_ablation_monthly_wf_refresh_v1.py
  Non-gating; no Track A / ensemble / live trading promotion.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-KospiLensAblationMonthlyWfRefresh_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$DateFrom = "1996-12-11",
    [string]$DateTo = "2026-06-05",
    [switch]$SkipFetch,
    [switch]$SkipJsonlBuild,
    [switch]$SkipPytest,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$args = @(
    "scripts\run_kospi_lens_ablation_monthly_wf_refresh_v1.py",
    "--date-from", $DateFrom,
    "--date-to", $DateTo
)
if ($SkipFetch) { $args += "--skip-fetch" }
if ($SkipJsonlBuild) { $args += "--skip-jsonl-build" }
if ($SkipPytest) { $args += "--skip-pytest" }
if ($DryRun) { $args += "--dry-run" }

& py @args
exit $LASTEXITCODE
