#Requires -Version 5.1
<#
.SYNOPSIS
  Copy F:\workspace_archive to a destination on another drive (default E:) via robocopy, then optionally remove the F: copy after verification.

.DESCRIPTION
  Intended to free F: when it is full (~291GB archive typical). Does NOT delete F: until -RemoveSourceAfterVerify is passed AND robocopy exit code is 0-7 (success/no extra files).

  E:\\ root often denies mkdir (policy). Default uses E:\\02_Projects\\... first; if creation fails, other E: subfolders are tried.

.EXAMPLE
  .\scripts\Migrate-FWorkspaceArchiveToE.ps1 -WhatIfSizesOnly
  .\scripts\Migrate-FWorkspaceArchiveToE.ps1
  .\scripts\Migrate-FWorkspaceArchiveToE.ps1 -DestinationRoot "D:\somewhere\MKM_ARCHIVE_FROM_F" -RemoveSourceAfterVerify
#>
param(
    [string]$Source = "F:\workspace_archive",
    [string]$DestinationRoot = "",
    [string]$WorkspaceRoot = "",
    [switch]$WhatIfSizesOnly,
    [switch]$RemoveSourceAfterVerify
)

$ErrorActionPreference = "Stop"
$repo = if ($WorkspaceRoot) { $WorkspaceRoot } else { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
$logDir = Join-Path $repo "reports"
if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
$logFile = Join-Path $logDir "workspace_archive_robocopy_$stamp.log"

function Get-DriveLetterFromPath([string]$path) {
    if ($path -match '^([A-Za-z]):\\') { return $Matches[1].ToUpperInvariant() }
    return $null
}

function Get-FreeGB([string]$letter) {
    $d = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$($letter):'" -ErrorAction SilentlyContinue
    if (-not $d) { return $null }
    return [math]::Round($d.FreeSpace / 1GB, 2)
}

function Resolve-DestinationRootFolder {
    param([string]$Preferred)
    $candidates = [System.Collections.Generic.List[string]]::new()
    if (-not [string]::IsNullOrWhiteSpace($Preferred)) {
        $candidates.Add($Preferred.Trim())
    }
    foreach ($p in @(
            "E:\02_Projects\MKM_ARCHIVE_FROM_F",
            "E:\05_User_Data\MKM_ARCHIVE_FROM_F",
            "E:\Backup\MKM_ARCHIVE_FROM_F",
            "E:\01_Development_Tools\MKM_ARCHIVE_FROM_F",
            "E:\MKM_ARCHIVE_FROM_F"
        )) {
        if (-not $candidates.Contains($p)) { $candidates.Add($p) }
    }
    $lastErr = $null
    foreach ($root in $candidates) {
        $drive = $root.Substring(0, 2)
        if (-not (Test-Path -LiteralPath $drive)) { continue }
        try {
            New-Item -ItemType Directory -Force -Path $root -ErrorAction Stop | Out-Null
            return $root
        }
        catch {
            $lastErr = $_.Exception.Message
        }
    }
    throw "Could not create any destination folder (tried user path + E: subfolders). Last error: $lastErr"
}

if (-not (Test-Path -LiteralPath $Source)) {
    Write-Error "Source not found: $Source"
    exit 2
}

$srcDrive = Get-DriveLetterFromPath $Source
$freeSrc = if ($srcDrive) { Get-FreeGB $srcDrive } else { $null }

Write-Host "=== Migrate F: workspace_archive ===" -ForegroundColor Cyan
Write-Host "Source:      $Source"
if ($WhatIfSizesOnly) {
    Write-Host "[WhatIf] No copy performed. Default/fallback roots: E:\02_Projects\..., E:\05_User_Data\..., E:\Backup\..., E:\ root." -ForegroundColor Yellow
    if ($null -ne $freeSrc) { Write-Host "Src ${srcDrive}: free ${freeSrc} GB" }
    exit 0
}

try {
    $DestinationRoot = Resolve-DestinationRootFolder -Preferred $DestinationRoot
}
catch {
    Write-Error $_.Exception.Message
    exit 3
}

$dest = Join-Path $DestinationRoot "workspace_archive"
$dstDrive = Get-DriveLetterFromPath $DestinationRoot
if (-not $dstDrive) {
    Write-Error "Could not parse drive from DestinationRoot: $DestinationRoot"
    exit 2
}
$freeDst = Get-FreeGB $dstDrive

Write-Host "DestinationRoot (resolved): $DestinationRoot"
Write-Host "Destination: $dest"
Write-Host "Log:         $logFile"
Write-Host "Dest ${dstDrive}: free ${freeDst} GB"
if ($null -ne $freeSrc) { Write-Host "Src ${srcDrive}: free ${freeSrc} GB" }

if ($null -ne $freeDst -and $freeDst -lt 50) {
    Write-Warning "Destination drive ${dstDrive}: has only ${freeDst} GB free; large copy may fail."
}

$args = @(
    $Source, $dest,
    "/E", "/COPY:DAT", "/DCOPY:T",
    "/R:2", "/W:5", "/MT:8",
    "/LOG:$logFile", "/TEE", "/NP"
)

Write-Host "Starting robocopy (this may take hours)..." -ForegroundColor Yellow
$p = Start-Process -FilePath "robocopy.exe" -ArgumentList $args -NoNewWindow -Wait -PassThru
$code = $p.ExitCode
Write-Host "robocopy exit code: $code (0-7 = success variants per robocopy docs)" -ForegroundColor $(if ($code -le 7) { "Green" } else { "Red" })

# Robocopy: 0-7 OK for sync semantics; 8+ error
if ($code -ge 8) {
    Write-Error "robocopy failed with exit $code — not removing source. See log: $logFile"
    exit $code
}

if ($RemoveSourceAfterVerify) {
    Write-Host "Removing source tree: $Source" -ForegroundColor Red
    Remove-Item -LiteralPath $Source -Recurse -Force -ErrorAction Stop
    Write-Host "Source removed." -ForegroundColor Green
}
else {
    Write-Host "Copy finished. Verify contents, then re-run with -RemoveSourceAfterVerify to delete F: copy (destructive)." -ForegroundColor DarkGray
}

exit 0
