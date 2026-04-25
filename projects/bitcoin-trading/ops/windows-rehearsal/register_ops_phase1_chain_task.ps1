param(
    [string]$TaskName = "\Bitcoin-Ops-Phase1-Chain-Daily",
    [string]$StartTime = "08:30",
    [switch]$IncludeVerifyAllGreen,
    [switch]$ExcludeConstitutionGates,
    [switch]$ExcludeStrict,
    [switch]$ExcludeShowroomDeployVerify,
    [switch]$IncludeBitcoinTradingOtelSmoke,
    [string]$TrackaDefaultLane = "c3_domain_gated"
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
if (-not $ExcludeShowroomDeployVerify) {
    $extra += " -IncludeShowroomDeployVerify"
}
if ($IncludeBitcoinTradingOtelSmoke) {
    $extra += " -IncludeBitcoinTradingOtelSmoke"
}
if ($TrackaDefaultLane -and $TrackaDefaultLane.Trim().Length -gt 0) {
    $lane = $TrackaDefaultLane.Trim().ToLowerInvariant()
    # Keep /TR short enough for schtasks limit by skipping explicit default.
    if ($lane -ne "c3_domain_gated") {
        $extra += " -TrackaDefaultLane " + $lane
    }
}

$tr = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`"$extra"
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
Write-Host ("Gate summary: constitution={0}, strict={1}, otel_smoke={2}, verify_all_green={3}, showroom_verify={4}" -f `
    (-not $ExcludeConstitutionGates), `
    (-not $ExcludeStrict), `
    [bool]$IncludeBitcoinTradingOtelSmoke, `
    [bool]$IncludeVerifyAllGreen, `
    (-not $ExcludeShowroomDeployVerify))
exit 0
