# Register (or remove) a Windows Scheduled Task for Run-BtrackCodebookCodepackPromotionChain.ps1.
# Lightweight daily drift + inventory + bridge; default SkipSignoff (unattended-safe). Use -Signoff to refresh packet.
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Btrack_Codebook_Codepack_Chain",
    [string]$DailyAt = "07:05",
    [switch]$Signoff,
    [switch]$RunNow
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$chain = Join-Path $workspaceRoot "scripts\Run-BtrackCodebookCodepackPromotionChain.ps1"
$schtasks = Join-Path $env:WINDIR "System32\schtasks.exe"
if (-not (Test-Path -LiteralPath $schtasks)) {
    $schtasks = "schtasks.exe"
}

function Invoke-SchTasks {
    param([string[]]$TaskArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        & $schtasks @TaskArgs 2>&1 | Out-Null
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prev
    }
}

if ($Remove) {
    $null = Invoke-SchTasks @("/Delete", "/TN", $TaskName, "/F")
    Write-Host "Removed scheduled task (if existed): $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $chain)) {
    throw "Chain script not found: $chain"
}

if ($DailyAt -notmatch '^\d{2}:\d{2}$') {
    throw "DailyAt must be HH:mm (24h, local machine clock), got: $DailyAt"
}

$tr = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$chain`""
if (-not $Signoff) { $tr += " -SkipSignoff" }

$null = Invoke-SchTasks @("/Delete", "/TN", $TaskName, "/F")
$createExit = Invoke-SchTasks @("/Create", "/TN", $TaskName, "/TR", $tr, "/SC", "DAILY", "/ST", $DailyAt, "/F")
if ($createExit -ne 0) {
    throw "schtasks /Create failed (exit=$createExit). Try elevated PowerShell (Run as administrator)."
}

Write-Host "Registered scheduled task: $TaskName"
Write-Host "Schedule: DAILY at $DailyAt (local machine time)"
Write-Host "Command: $tr"

if ($RunNow) {
    Write-Host "RunNow: invoking chain in current session..." -ForegroundColor DarkGray
    $rn = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $chain)
    if (-not $Signoff) { $rn += "-SkipSignoff" }
    & powershell.exe @rn
    if ($LASTEXITCODE -ne 0) {
        throw "RunNow chain failed exit=$LASTEXITCODE"
    }
}

exit 0
