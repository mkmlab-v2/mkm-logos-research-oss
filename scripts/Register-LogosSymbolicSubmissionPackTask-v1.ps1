param(
    [string]$TaskName = "MKM-LogosSymbolic-SubmissionPack-Daily",
    [string]$At = "21:30",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$Approver = "PRO",
    [switch]$SkipConstitutionGate,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\run_logos_symbolic_submission_pack_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "missing runner script: $runner"
}

$args = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$runner`"",
    "-Approver", "`"$Approver`""
)
if ($SkipConstitutionGate) {
    $args += "-SkipConstitutionGate"
}

$taskRun = "powershell " + ($args -join " ")
$createCmd = @(
    "schtasks",
    "/Create",
    "/TN", "`"$TaskName`"",
    "/SC", "DAILY",
    "/ST", $At,
    "/TR", "`"$taskRun`"",
    "/F"
) -join " "

$queryCmd = "schtasks /Query /TN `"$TaskName`" /V /FO LIST"

Write-Host "TASK_NAME: $TaskName"
Write-Host "SCHEDULE : DAILY @ $At"
Write-Host "RUNNER   : $runner"
Write-Host "COMMAND  : $taskRun"

if ($DryRun) {
    Write-Host ""
    Write-Host "[DRY-RUN] create command:"
    Write-Host $createCmd
    Write-Host ""
    Write-Host "[DRY-RUN] query command:"
    Write-Host $queryCmd
    exit 0
}

cmd /c $createCmd
cmd /c $queryCmd

Write-Host "DONE: scheduled task registered."

