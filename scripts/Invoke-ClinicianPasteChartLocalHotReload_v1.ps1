#Requires -Version 5.1
<#
.SYNOPSIS
  Paste Chart local hot reload — Next.js :3010 + browser (no VPS deploy).

.EXAMPLE
  powershell -File scripts\Invoke-ClinicianPasteChartLocalHotReload_v1.ps1
.EXAMPLE
  powershell -File scripts\Invoke-ClinicianPasteChartLocalHotReload_v1.ps1 -OpenOnly
#>
param(
    [string]$No1kmediRoot = "C:\workspace\projects\no1kmedi",
    [string]$Email = "moksorinw@gmail.com",
    [int]$Port = 3010,
    [switch]$OpenOnly
)

$ErrorActionPreference = "Stop"

function Test-PortListening([int]$p) {
    try {
        $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        return [bool]$c
    } catch {
        return $false
    }
}

function Test-HttpOk([string]$url) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 8 -MaximumRedirection 5
        return $r.StatusCode -ge 200 -and $r.StatusCode -lt 400
    } catch {
        return $false
    }
}

function Wait-HttpOk([string]$url, [int]$timeoutSec = 90) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    $attempt = 0
    while ((Get-Date) -lt $deadline) {
        $attempt++
        if (Test-HttpOk $url) {
            Write-Host "[paste-chart-local] HTTP ready ($attempt)" -ForegroundColor DarkGray
            return
        }
        if ($attempt -eq 1 -or ($attempt % 5) -eq 0) {
            Write-Host "[paste-chart-local] waiting for $url ... ($attempt)" -ForegroundColor DarkYellow
        }
        Start-Sleep -Seconds 2
    }
    throw "timeout waiting for $url (is Next dev compiling on :$Port?)"
}

$baseUrl = "http://127.0.0.1:${Port}"
$probeUrl = "$baseUrl/clinician?panel=gold"
$panelUrl = "$probeUrl&email=$([uri]::EscapeDataString($Email))"

if (-not $OpenOnly) {
    if (-not (Test-PortListening $Port)) {
        Write-Host "[paste-chart-local] starting next dev on :$Port" -ForegroundColor Cyan
        Start-Process -FilePath "cmd.exe" -ArgumentList @(
            "/c", "cd /d `"$No1kmediRoot`" && npm run dev"
        ) -WindowStyle Minimized
    } else {
        Write-Host "[paste-chart-local] :$Port already listening" -ForegroundColor DarkGray
    }
    Wait-HttpOk $probeUrl
} elseif (-not (Test-HttpOk $probeUrl)) {
    throw "OpenOnly: $probeUrl not ready — run without -OpenOnly first"
}

Write-Host "[paste-chart-local] open $panelUrl" -ForegroundColor Green
Start-Process $panelUrl

Write-Host @"

Hot reload: edit projects/no1kmedi/src/** — browser auto-refreshes (Next HMR).
Open only:  powershell -File scripts\Invoke-ClinicianPasteChartLocalHotReload_v1.ps1 -OpenOnly
Verify:     `$env:NO1KMEDI_BASE_URL='http://127.0.0.1:3010'; node projects/no1kmedi/scripts/verify-paste-chart-slash-header-self-v1.mjs
"@
