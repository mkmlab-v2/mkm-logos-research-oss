#Requires -Version 5.1
<#
.SYNOPSIS
  OI 20460237 — 붙임1 사업계획서 HWPX/HWP auto-fill from paste SSOT.
#>
param(
    [string]$TemplateHwpx = "",
    [switch]$SkipHancom
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$pyArgs = @("scripts/run_kstartup_open_innovation_20460237_hwpx_fill_v1.py")
if ($TemplateHwpx) { $pyArgs += @("--template-hwpx", $TemplateHwpx) }
if ($SkipHancom) { $pyArgs += "--skip-hancom" }
py @pyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
