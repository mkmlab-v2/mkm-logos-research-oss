# Register (or remove) a Windows Scheduled Task for Run-BtrackInsightSidecarChain.ps1.
# Default: daily local time, SkipSignoff (unattended-safe); use -Signoff to run signoff in the task.
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Btrack_Insight_Sidecar_Chain",
    [string]$DailyAt = "07:20",
    [switch]$Signoff,
    [switch]$IncludeMultilensRefresh,
    [switch]$SkipNotebooklmKpi,
    [switch]$RunNow
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$chain = Join-Path $workspaceRoot "scripts\Run-BtrackInsightSidecarChain.ps1"

if ($Remove) {
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
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
if ($IncludeMultilensRefresh) { $tr += " -IncludeMultilensRefresh" }
if ($SkipNotebooklmKpi) { $tr += " -SkipNotebooklmKpi" }

schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
schtasks /Create /TN $TaskName /TR $tr /SC DAILY /ST $DailyAt /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "schtasks /Create failed (exit=$LASTEXITCODE). Try elevated PowerShell."
}

Write-Host "Registered scheduled task: $TaskName"
Write-Host "Schedule: DAILY at $DailyAt (local machine time)"
Write-Host "Command: $tr"

if ($RunNow) {
    Write-Host "RunNow: invoking chain in current session..." -ForegroundColor DarkGray
    $rn = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $chain)
    if (-not $Signoff) { $rn += "-SkipSignoff" }
    if ($IncludeMultilensRefresh) { $rn += "-IncludeMultilensRefresh" }
    if ($SkipNotebooklmKpi) { $rn += "-SkipNotebooklmKpi" }
    & powershell.exe @rn
    if ($LASTEXITCODE -ne 0) {
        throw "RunNow chain failed exit=$LASTEXITCODE"
    }
}

exit 0
