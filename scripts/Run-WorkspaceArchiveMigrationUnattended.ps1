#Requires -Version 5.1
<#
.SYNOPSIS
  Runs workspace_archive migration in two stages outside short-lived agent shells:
  1) Migrate-FWorkspaceArchiveToE.ps1 (robocopy; safe to re-run = resume)
  2) Same script with -RemoveSourceAfterVerify (quick sync + delete F:\workspace_archive)

.EXAMPLE
  # Foreground (blocks until done — can take hours):
  .\scripts\Run-WorkspaceArchiveMigrationUnattended.ps1

  # Detached (own PowerShell window):
  Start-Process pwsh -WorkingDirectory C:\workspace -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\workspace\scripts\Run-WorkspaceArchiveMigrationUnattended.ps1'
#>
param(
  [switch]$SkipRemoveSource
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repo
$migrate = Join-Path $PSScriptRoot 'Migrate-FWorkspaceArchiveToE.ps1'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd_HHmmss')
$marker = Join-Path $repo "reports\workspace_archive_unattended_$stamp.log"

function Invoke-MigrateStage {
  param([string[]]$ExtraArgs)
  $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $migrate) + $ExtraArgs
  $p = Start-Process -FilePath 'pwsh.exe' -ArgumentList $argList -WorkingDirectory $repo -Wait -PassThru -NoNewWindow
  return $p.ExitCode
}

"START $stamp" | Set-Content -LiteralPath $marker -Encoding utf8

Write-Host "=== Unattended workspace_archive migration ===" -ForegroundColor Cyan
Write-Host "Marker: $marker"

Write-Host "`n[1/2] Robocopy F:\workspace_archive -> E: (resumes if interrupted)..." -ForegroundColor Yellow
$c1 = Invoke-MigrateStage @()
"STAGE1_EXIT=$c1" | Add-Content -LiteralPath $marker -Encoding utf8
if ($c1 -ne 0) {
  Write-Error "Stage 1 failed with exit $c1. Not removing source. See reports\workspace_archive_robocopy_*.log"
  exit $c1
}

if ($SkipRemoveSource) {
  Write-Host "SkipRemoveSource: done after copy only." -ForegroundColor DarkGray
  exit 0
}

Write-Host "`n[2/2] Sync pass + remove F:\workspace_archive ..." -ForegroundColor Yellow
$c2 = Invoke-MigrateStage @('-RemoveSourceAfterVerify')
"STAGE2_EXIT=$c2" | Add-Content -LiteralPath $marker -Encoding utf8
if ($c2 -ne 0) {
  Write-Error "Stage 2 failed with exit $c2 (source may still exist on F:)."
  exit $c2
}

Write-Host "`nAll stages OK." -ForegroundColor Green
exit 0
