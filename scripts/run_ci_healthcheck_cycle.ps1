param(
    [int]$Limit = 5,
    [switch]$RunNumericNearMissGateCheck,
    [switch]$ApproveNumericNearMiss
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$healthcheck = Join-Path $workspaceRoot "scripts\ops\ci_healthcheck.ps1"
$logDir = Join-Path $workspaceRoot "reports\constitution\btrack_pilot\ops"

if (-not (Test-Path -LiteralPath $healthcheck)) {
    throw "Healthcheck script not found: $healthcheck"
}

if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$ts = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss_fff")
$nonce = [System.Guid]::NewGuid().ToString("N").Substring(0, 6)
$logPath = Join-Path $logDir "ci_healthcheck_cycle_${ts}_${nonce}.log"

"[$((Get-Date).ToString('s'))] Starting ci_healthcheck cycle (limit=$Limit)" | Out-File -FilePath $logPath -Encoding utf8

try {
    # Do not force failed-log extraction here; in-progress runs can make gh return non-zero.
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $healthcheck,
        "-Limit", $Limit
    )
    if ($RunNumericNearMissGateCheck) {
        $args += "-RunNumericNearMissGateCheck"
    }
    if ($ApproveNumericNearMiss) {
        $args += "-ApproveNumericNearMiss"
    }
    & powershell.exe @args *>&1 | Tee-Object -FilePath $logPath -Append
    "[$((Get-Date).ToString('s'))] Completed OK" | Out-File -FilePath $logPath -Append -Encoding utf8
}
catch {
    "[$((Get-Date).ToString('s'))] FAILED: $($_.Exception.Message)" | Out-File -FilePath $logPath -Append -Encoding utf8
    throw
}
