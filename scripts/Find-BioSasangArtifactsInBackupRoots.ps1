#Requires -Version 5.1
<#
.SYNOPSIS
  Search common backup / archive roots for bio_sasang-related files (read-only).

.DESCRIPTION
  Uses a single PowerShell process (no nested pwsh -Command) so foreach/variables
  are not stripped by quoting. Default roots match AGENTS.md / cleanup runbook
  destinations; E: is not scanned by default (full-disk recurse is too slow).

.PARAMETER BackupRoot
  One or more directories to search. Each must be passed explicitly if overriding defaults.

.PARAMETER Depth
  Recursion depth per root (default 6).

.PARAMETER Filter
  Get-ChildItem -Filter pattern (default '*bio_sasang*').

.PARAMETER IncludeWorkspaceReports
  Also scan repo `reports/` for the same filter (quick sanity vs backups).

.EXAMPLE
  pwsh -NoProfile -File scripts/Find-BioSasangArtifactsInBackupRoots.ps1

.EXAMPLE
  pwsh -NoProfile -File scripts/Find-BioSasangArtifactsInBackupRoots.ps1 -BackupRoot @('D:\archives\mkm') -Depth 8
#>

[CmdletBinding()]
param(
    [string[]] $BackupRoot = @(
        'F:\BACKUP\C_ROOT_MIGRATED_FROM_C',
        'F:\workspace_archive',
        'C:\workspace\storage\MKM_ARCHIVE_FROM_F'
    ),
    [ValidateRange(0, 32)]
    [int] $Depth = 6,
    [string] $Filter = '*bio_sasang*',
    [switch] $IncludeWorkspaceReports
)

$ErrorActionPreference = 'Continue'

function Write-Section([string] $Title) {
    Write-Host ""
    Write-Host "== $Title ==" -ForegroundColor Cyan
}

Write-Section "Find-BioSasangArtifactsInBackupRoots"
Write-Host "Filter: $Filter | Depth: $Depth"
Write-Host "Roots: $($BackupRoot -join '; ')"

$all = New-Object System.Collections.Generic.List[string]

foreach ($root in $BackupRoot) {
    if (-not $root) { continue }
    if (-not (Test-Path -LiteralPath $root)) {
        Write-Host "[SKIP] Missing: $root" -ForegroundColor DarkYellow
        continue
    }
    Write-Host "[SCAN] $root"
    $hits = Get-ChildItem -LiteralPath $root -Filter $Filter -Recurse -Depth $Depth -File -ErrorAction SilentlyContinue
    foreach ($h in $hits) {
        $p = $h.FullName
        Write-Host "  $p"
        [void]$all.Add($p)
    }
}

if ($IncludeWorkspaceReports) {
    $repoRoot = Split-Path -Parent $PSScriptRoot
    $reports = Join-Path $repoRoot 'reports'
    if (Test-Path -LiteralPath $reports) {
        Write-Section "Workspace reports ($reports)"
        $hits = Get-ChildItem -LiteralPath $reports -Filter $Filter -Recurse -Depth 3 -File -ErrorAction SilentlyContinue
        foreach ($h in $hits) {
            $p = $h.FullName
            Write-Host "  $p"
            [void]$all.Add($p)
        }
    }
    else {
        Write-Host "[SKIP] Missing reports dir: $reports" -ForegroundColor DarkYellow
    }
}

Write-Section "Summary"
Write-Host "Total matches: $($all.Count)"
if ($all.Count -eq 0) {
    Write-Host "No files matched. Re-run with -IncludeWorkspaceReports or add -BackupRoot paths." -ForegroundColor DarkGray
}

exit 0
