$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-Fused-QuantPixel-SOP-Strict-Check"
$startTime = "09:15"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\run_fused_quant_pixel_sop.ps1"
$gatewayEnsure = Join-Path $projectRoot "ops\windows-rehearsal\ensure_public_event_gateway.ps1"
$assertScript = Join-Path $projectRoot "ops\windows-rehearsal\assert_task_target_exists.ps1"

& powershell -ExecutionPolicy Bypass -File $assertScript -TargetPath $runner -Label "Fused SOP runner"
& powershell -ExecutionPolicy Bypass -File $assertScript -TargetPath $gatewayEnsure -Label "Gateway ensure script"

$maxRetries = 3
$attempt = 1
$lastExitCode = 0
while ($attempt -le $maxRetries) {
    & powershell -ExecutionPolicy Bypass -File $gatewayEnsure -Strict
    $lastExitCode = $LASTEXITCODE
    if ($lastExitCode -eq 0) { break }
    if ($attempt -lt $maxRetries) { Start-Sleep -Seconds 2 }
    $attempt += 1
}
if ($lastExitCode -ne 0) {
    throw "Strict gateway pre-check failed after $maxRetries attempts. ExitCode=$lastExitCode"
}

$argParts = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$runner`"",
    "-Phase1Mode", "skip",
    "-StrictGateway"
)
$tr = "powershell " + ($argParts -join " ")

schtasks /Query /TN $taskName > $null 2>&1
if ($LASTEXITCODE -eq 0) {
    schtasks /Delete /TN $taskName /F | Out-Null
}
schtasks /Create /TN $taskName /SC DAILY /ST $startTime /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create strict-check task. ExitCode=$LASTEXITCODE"
}

Write-Host "Created scheduled strict-check task: $taskName"
Write-Host "Start time: $startTime"
Write-Host "Command: $tr"
