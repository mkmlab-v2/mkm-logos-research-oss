#Requires -Version 5.1
<#
.SYNOPSIS
  P0: Regenerate reports/bio_sasang_nstates_strict_comparison_v2.json (rehydrate v1).

.DESCRIPTION
  Calls build_bio_sasang_nstates_strict_comparison_rehydrate_v1.py — deterministic
  JSON with regeneration.mode=rehydrated_from_ssot_documentation (not a fresh
  FireProt recompute). Optionally runs Find-BioSasangArtifactsInBackupRoots.ps1
  for audit.

.PARAMETER SkipBackupScan
  Do not run Find-BioSasangArtifactsInBackupRoots.ps1 after rehydrate.

.PARAMETER Python
  Python launcher (default: py).

.PARAMETER OutJson
  Passed through to rehydrate --out (default: reports/... under repo root).
#>

[CmdletBinding()]
param(
    [switch] $SkipBackupScan,
    [string] $Python = "py",
    [string] $OutJson = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

$rehydrate = Join-Path $RepoRoot "scripts\build_bio_sasang_nstates_strict_comparison_rehydrate_v1.py"
if (-not (Test-Path -LiteralPath $rehydrate)) {
    throw "Missing rehydrate script: $rehydrate"
}

$args = @("-3", $rehydrate)
if ($OutJson) {
    $args += @("--out", $OutJson)
}

Write-Host "[BioSasang] Rehydrating n-states strict comparison..." -ForegroundColor Cyan
& $Python @args
if ($LASTEXITCODE -ne 0) {
    throw "Rehydrate script failed (exit $LASTEXITCODE)."
}

if (-not $SkipBackupScan) {
    $finder = Join-Path $RepoRoot "scripts\Find-BioSasangArtifactsInBackupRoots.ps1"
    if (Test-Path -LiteralPath $finder) {
        Write-Host "[BioSasang] Backup + reports scan (informational)..." -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File $finder -IncludeWorkspaceReports
    }
}

Write-Host "[BioSasang] Done." -ForegroundColor Green
exit 0
