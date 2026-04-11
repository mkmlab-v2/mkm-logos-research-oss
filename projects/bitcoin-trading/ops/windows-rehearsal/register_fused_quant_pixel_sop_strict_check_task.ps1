$ErrorActionPreference = "Stop"

$taskName = "Bitcoin-Fused-QuantPixel-SOP-Strict-Check"
$startTime = "09:15"
$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\run_fused_quant_pixel_sop.ps1"
$gatewayEnsure = Join-Path $projectRoot "ops\windows-rehearsal\ensure_public_event_gateway.ps1"
$assertScript = Join-Path $projectRoot "ops\windows-rehearsal\assert_task_target_exists.ps1"

& powershell -ExecutionPolicy Bypass -File $assertScript -TargetPath $runner -Label "Fused SOP runner"
& powershell -ExecutionPolicy Bypass -File $assertScript -TargetPath $gatewayEnsure -Label "Gateway ensure script"

# Pre-check in strict mode before scheduling (bounded retry for transient contention).
$maxRetries = 3
$attempt = 1
$lastExitCode = 0
while ($attempt -le $maxRetries) {
    & powershell -ExecutionPolicy Bypass -File $gatewayEnsure -Strict
    $lastExitCode = $LASTEXITCODE
    if ($lastExitCode -eq 0) {
        break
    }
    if ($attempt -lt $maxRetries) {
        Start-Sleep -Seconds 2
    }
    $attempt += 1
}
if ($lastExitCode -ne 0) {
    throw "Strict gateway pre-check failed after $maxRetries attempts. ExitCode=$lastExitCode"
}

function Test-GatewayLatestEndpoint([int]$Port = 8788) {
    try {
        $url = "http://127.0.0.1:{0}/api/public-events/latest" -f $Port
        $req = [System.Net.HttpWebRequest]::Create($url)
        $req.Method = "GET"
        $req.Timeout = 5000
        $req.ReadWriteTimeout = 5000
        $req.Proxy = $null
        $resp = $req.GetResponse()
        $statusCode = [int]$resp.StatusCode
        $resp.Close()
        return ($statusCode -ge 200 -and $statusCode -lt 400)
    } catch {
        return $false
    }
}

if (-not (Test-GatewayLatestEndpoint -Port 8788)) {
    throw "Gateway HTTP probe failed after strict pre-check."
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
schtasks /Query /TN $taskName > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Task created command returned success but query failed for task '$taskName'."
}

Write-Host "Created scheduled strict-check task: $taskName"
Write-Host "Start time: $startTime"
Write-Host "Command: $tr"
