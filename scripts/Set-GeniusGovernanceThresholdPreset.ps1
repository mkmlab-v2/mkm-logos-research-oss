<#
.SYNOPSIS
  Apply a genius governance threshold preset to operating profile.
#>
param(
    [ValidateSet("conservative", "aggressive")]
    [string]$Preset = "conservative",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$profilePath = Join-Path $WorkspaceRoot "docs\final\artifacts\cursor_ai_operating_profile_v1_latest.json"
$presetPath = Join-Path $WorkspaceRoot "docs\final\artifacts\genius_governance_threshold_presets_v1.json"

if (-not (Test-Path -LiteralPath $profilePath)) { throw "Profile not found: $profilePath" }
if (-not (Test-Path -LiteralPath $presetPath)) { throw "Preset file not found: $presetPath" }

$profile = Get-Content -LiteralPath $profilePath -Raw | ConvertFrom-Json
$presetDoc = Get-Content -LiteralPath $presetPath -Raw | ConvertFrom-Json
$presets = $presetDoc.presets
if ($null -eq $presets.$Preset) { throw "Preset not found: $Preset" }

$profile.genius_governance = $presets.$Preset
$profile | Add-Member -NotePropertyName "genius_governance_active_preset" -NotePropertyValue $Preset -Force

$json = $profile | ConvertTo-Json -Depth 30
Set-Content -LiteralPath $profilePath -Value ($json + "`n") -Encoding UTF8

Write-Host "Applied genius governance preset: $Preset"
Write-Host "Profile: $profilePath"
