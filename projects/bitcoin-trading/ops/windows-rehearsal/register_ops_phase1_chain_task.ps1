param(
    [string]$TaskName = "\Bitcoin-Ops-Phase1-Chain-Daily",
    [string]$StartTime = "08:30",
    [switch]$IncludeVerifyAllGreen,
    [switch]$ExcludeConstitutionGates,
    [switch]$ExcludeStrict
)

$ErrorActionPreference = "Stop"

$scriptPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_ops_phase1_chain.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing $scriptPath"
}

$extra = ""
if ($IncludeVerifyAllGreen) {
    $extra = " -IncludeVerifyAllGreen"
}
if (-not $ExcludeConstitutionGates) {
    $extra += " -IncludeConstitutionGates"
}
if (-not $ExcludeStrict) {
    $extra += " -Strict"
}

$tr = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"$extra"
if ($tr.Length -gt 261) {
    throw "/TR exceeds 261 chars; omit switches or shorten paths."
}

$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
schtasks /Delete /TN $TaskName /F 2>&1 | Out-Null
$ErrorActionPreference = $oldEap

schtasks /Create /TN $TaskName /SC DAILY /ST $StartTime /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "schtasks create failed for $TaskName"
}

Write-Host "Created daily task: $TaskName at $StartTime"
Write-Host "TR: $tr"
exit 0
