<#
.SYNOPSIS
  One-click chain: train -> approve/reject -> apply(weather fusion profile) for myeongni v2.

.DESCRIPTION
  Executes:
   1) train_myeongni_weather_fusion_profile_v1.py
   2) approve_myeongni_weather_fusion_profile_v1.py (--approve/--reject)
   3) build_mkm_myeongni_response_v2.py --apply-weather-fusion-profile
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Approve,
    [switch]$Reject,
    [string]$Reviewer = "PRO",
    [string]$Note = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

if ($Approve -and $Reject) {
    throw "Choose only one of -Approve or -Reject."
}
if (-not $Approve -and -not $Reject) {
    $Approve = $true
}

$train = "py scripts\train_myeongni_weather_fusion_profile_v1.py"
$approveFlag = if ($Reject) { "--reject" } else { "--approve" }
$approveCmd = "py scripts\approve_myeongni_weather_fusion_profile_v1.py $approveFlag --reviewer `"$Reviewer`""
if ($Note -and $Note.Trim().Length -gt 0) {
    $approveCmd = "$approveCmd --note `"$Note`""
}
$apply = "py scripts\build_mkm_myeongni_response_v2.py --apply-weather-fusion-profile"

if ($DryRun) {
    Write-Host "[DryRun] $train"
    Write-Host "[DryRun] $approveCmd"
    Write-Host "[DryRun] $apply"
    exit 0
}

Write-Host "[1/3] Training weather fusion profile..."
Invoke-Expression $train
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] Manual approval lock..."
Invoke-Expression $approveCmd
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/3] Apply profile in myeongni v2 response..."
Invoke-Expression $apply
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DONE: train -> approve/reject -> apply chain completed."
exit 0

