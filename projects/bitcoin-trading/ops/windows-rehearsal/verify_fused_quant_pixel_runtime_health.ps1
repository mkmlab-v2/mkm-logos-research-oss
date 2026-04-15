param(
    [int]$GatewayPort = 8788,
    [string]$TaskName = "Bitcoin-Fused-QuantPixel-SOP-Strict-Check",
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\runtime_health_latest.json"
)

$ErrorActionPreference = "Stop"

function Test-GatewayLatestEndpoint([int]$Port) {
    $probeHosts = @("127.0.0.1", "localhost")
    try {
        $ipRows = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object {
                $_.IPAddress -and
                $_.IPAddress -notlike "127.*" -and
                $_.IPAddress -ne "0.0.0.0"
            } |
            Select-Object -ExpandProperty IPAddress -Unique
        if ($ipRows) {
            $probeHosts += @($ipRows)
        }
    } catch {
        # keep default loopback probes only
    }

    $lastError = $null
    $attemptsPerHost = 3
    foreach ($probeHost in $probeHosts | Select-Object -Unique) {
        $url = "http://{0}:{1}/api/public-events/latest" -f $probeHost, $Port
        for ($attempt = 1; $attempt -le $attemptsPerHost; $attempt++) {
            try {
                $req = [System.Net.HttpWebRequest]::Create($url)
                $req.Method = "GET"
                $req.Timeout = 5000
                $req.ReadWriteTimeout = 5000
                $req.Proxy = $null
                $req.KeepAlive = $false
                $resp = $req.GetResponse()
                $statusCode = [int]$resp.StatusCode
                $resp.Close()
                if ($statusCode -ge 200 -and $statusCode -lt 400) {
                    return @{
                        ok = $true
                        status_code = $statusCode
                        probe_host = $probeHost
                        probe_url = $url
                        probe_attempt = $attempt
                    }
                }
                $lastError = "status_code=$statusCode host=$probeHost attempt=$attempt"
            } catch {
                $lastError = "$($_.Exception.Message) host=$probeHost attempt=$attempt"
                Start-Sleep -Milliseconds 300
            }
        }
    }

    return @{
        ok = $false
        status_code = -1
        error = $lastError
        probe_hosts = $probeHosts
    }
}

function Get-ScheduledTaskInfo([string]$Name) {
    schtasks /Query /TN $Name /V /FO LIST > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        return @{
            exists = $false
            status = "NOT_FOUND"
        }
    }

    $raw = schtasks /Query /TN $Name /V /FO LIST
    $statusLine = $raw | Where-Object { $_ -match "^Status:\s+" } | Select-Object -First 1
    $nextRunLine = $raw | Where-Object { $_ -match "^Next Run Time:\s+" } | Select-Object -First 1
    return @{
        exists = $true
        status = ($statusLine -replace "^Status:\s+", "").Trim()
        next_run_time = ($nextRunLine -replace "^Next Run Time:\s+", "").Trim()
    }
}

$strictEnsureScript = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\ensure_public_event_gateway.ps1"
& powershell -ExecutionPolicy Bypass -File $strictEnsureScript -Strict
$strictExit = $LASTEXITCODE

$gateway = Test-GatewayLatestEndpoint -Port $GatewayPort
$task = Get-ScheduledTaskInfo -Name $TaskName

$result = [ordered]@{
    timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    strict_ensure_exit_code = $strictExit
    gateway = $gateway
    scheduled_task = $task
}

$taskReady = $task.exists -and ($task.status -in @("Ready", "Running"))
$ok = ($strictExit -eq 0) -and $gateway.ok -and $taskReady
$result["overall_ok"] = $ok

$json = $result | ConvertTo-Json -Depth 6
Write-Host $json

if ($OutputPath -and $OutputPath.Trim().Length -gt 0) {
    $parent = Split-Path -Parent $OutputPath
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
    Write-Host ("Saved runtime health report: {0}" -f $OutputPath)
}

if (-not $ok) {
    exit 1
}
exit 0
