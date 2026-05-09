[CmdletBinding()]
param(
    [int]$StartupDelaySec = 45,
    [int]$HealthTimeoutSec = 60,
    [string]$LockName = "Global\MKM_N8N_SERVICE_GUARD_V1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-N8nHealth {
    try {
        Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:5678/rest/settings" -TimeoutSec 5 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Get-N8nStartProcess {
    return @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -and $_.CommandLine -match "\bn8n(\.cmd)?\b.*\bstart\b" }
    )
}

function Resolve-N8nCmdPath {
    try {
        $cmd = (Get-Command -Name "n8n.cmd" -ErrorAction Stop).Source
        if (Test-Path -LiteralPath $cmd) {
            return $cmd
        }
    } catch {
        return $null
    }
    return $null
}

$mutex = [System.Threading.Mutex]::new($false, $LockName)
$hasLock = $false
try {
    $hasLock = $mutex.WaitOne(0)
    if (-not $hasLock) {
        Write-Output "n8n_guard: lock_busy -> another guard instance active"
        exit 0
    }

    if ($StartupDelaySec -gt 0) {
        Start-Sleep -Seconds $StartupDelaySec
    }

    if (Test-N8nHealth) {
        Write-Output "n8n_guard: healthy_already"
        exit 0
    }

    $existing = @(Get-N8nStartProcess)
    if (@($existing).Count -gt 0) {
        Write-Output "n8n_guard: process_exists_waiting_health"
    } else {
        $n8nCmd = Resolve-N8nCmdPath
        if ([string]::IsNullOrWhiteSpace($n8nCmd)) {
            Write-Output "n8n_guard: n8n_cmd_not_found"
            exit 3
        }
        Start-Process -FilePath $n8nCmd -WindowStyle Hidden -ArgumentList "start"
        Write-Output "n8n_guard: started_n8n"
    }

    $deadline = (Get-Date).AddSeconds($HealthTimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-N8nHealth) {
            Write-Output "n8n_guard: health_pass"
            exit 0
        }
        Start-Sleep -Seconds 2
    }

    Write-Output "n8n_guard: health_timeout"
    exit 2
}
finally {
    if ($hasLock) {
        $mutex.ReleaseMutex() | Out-Null
    }
    $mutex.Dispose()
}
