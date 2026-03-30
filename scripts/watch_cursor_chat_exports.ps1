#requires -Version 5.1
<#
.SYNOPSIS
  Watch (or batch-run) Cursor chat exports dropped into the inbox folder; run cursor_session_distill.py and archive sources.

.DESCRIPTION
  Default inbox: memory/obsidian_vault/_cursor_session_staging/inbox
  Processed files move to inbox/processed. Failures move to inbox/failed.

.PARAMETER Mode
  Once = process current files then exit. Watch = poll inbox every IntervalSeconds until Ctrl+C.

.PARAMETER Inbox
  Folder where you save exported .md / .txt chat logs.

.PARAMETER NoRawStaging
  Omit --write-raw-staging (default: keep full raw copy under _cursor_session_staging/raw).
#>
[CmdletBinding()]
param(
    [ValidateSet("Once", "Watch")]
    [string] $Mode = "Once",

    [string] $Inbox = "",

    [int] $IntervalSeconds = 5,

    [switch] $NoRawStaging
)

$ErrorActionPreference = "Stop"
# PSScriptRoot = .../scripts  →  repo root is parent
$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not $RepoRoot) { $RepoRoot = (Get-Location).Path }
if ([string]::IsNullOrWhiteSpace($Inbox)) {
    $Inbox = Join-Path $RepoRoot "memory\obsidian_vault\_cursor_session_staging\inbox"
}

$ProcessedDir = Join-Path $Inbox "processed"
$FailedDir = Join-Path $Inbox "failed"
$DistillScript = Join-Path $RepoRoot "scripts\cursor_session_distill.py"

foreach ($d in @($Inbox, $ProcessedDir, $FailedDir)) {
    if (-not (Test-Path -LiteralPath $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
    }
}

if (-not (Test-Path -LiteralPath $DistillScript)) {
    throw "Missing $DistillScript"
}

function Wait-StableFile {
    param(
        [string] $LiteralPath,
        [int] $MaxWaitSec = 45
    )
    $deadline = (Get-Date).AddSeconds($MaxWaitSec)
    $prevLen = $null
    $stableCount = 0
    while ((Get-Date) -lt $deadline) {
        $item = Get-Item -LiteralPath $LiteralPath -ErrorAction SilentlyContinue
        if (-not $item) { return $false }
        if ($prevLen -eq $item.Length) {
            $stableCount++
            if ($stableCount -ge 2) { return $true }
        } else {
            $stableCount = 0
            $prevLen = $item.Length
        }
        Start-Sleep -Milliseconds 600
    }
    return $true
}

function Invoke-OneExport {
    param([System.IO.FileInfo] $File)

    $ext = $File.Extension.ToLowerInvariant()
    if ($ext -notin @(".md", ".txt")) { return }
    $full = $File.FullName
    $slug = [System.IO.Path]::GetFileNameWithoutExtension($File.Name)
    if ([string]::IsNullOrWhiteSpace($slug)) { $slug = "session" }

    Write-Host "[cursor-distill] processing: $full"

    if (-not (Wait-StableFile -LiteralPath $full)) {
        Write-Warning "File disappeared: $full"
        return
    }

    $argList = @(
        $DistillScript,
        "-i", $full,
        "--session-slug", $slug,
        "--session-ref", $full
    )
    if (-not $NoRawStaging) {
        $argList += "--write-raw-staging"
    }

    $process = Start-Process -FilePath "py" -ArgumentList $argList -NoNewWindow -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        Write-Warning "distill failed (exit $($process.ExitCode)): $full"
        $destName = "{0:yyyyMMdd_HHmmss}_{1}" -f (Get-Date), $File.Name
        Move-Item -LiteralPath $full -Destination (Join-Path $FailedDir $destName) -Force
        return
    }

    $destNameOK = "{0:yyyyMMdd_HHmmss}_{1}" -f (Get-Date), $File.Name
    Move-Item -LiteralPath $full -Destination (Join-Path $ProcessedDir $destNameOK) -Force
    Write-Host "[cursor-distill] archived to processed: $($File.Name)"
}

function Get-InboxCandidates {
    Get-ChildItem -LiteralPath $Inbox -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Extension -match "\.(md|txt)$" -and
            $_.Name -notmatch '^\.' 
        }
}

if ($Mode -eq "Once") {
    $items = @(Get-InboxCandidates)
    if ($items.Count -eq 0) {
        Write-Host "No .md/.txt in inbox: $Inbox"
        exit 0
    }
    foreach ($f in $items) {
        Invoke-OneExport -File $f
    }
    exit 0
}

Write-Host "Watching inbox (every ${IntervalSeconds}s): $Inbox"
Write-Host "Drop Cursor chat exports here as .md or .txt. Ctrl+C to stop."

while ($true) {
    foreach ($f in @(Get-InboxCandidates)) {
        try {
            Invoke-OneExport -File $f
        } catch {
            Write-Warning $_
        }
    }
    Start-Sleep -Seconds $IntervalSeconds
}
