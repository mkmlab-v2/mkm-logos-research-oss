#Requires -Version 5.1
<#
.SYNOPSIS
  Fully automated Paste Chart local loop: HMR dev + clipboard + API analyze + optional Tauri gate.

.EXAMPLE
  powershell -File scripts\Invoke-ClinicianPasteChartAutoDev_v1.ps1
.EXAMPLE
  powershell -File scripts\Invoke-ClinicianPasteChartAutoDev_v1.ps1 -SkipTauri
#>
param(
    [string]$Email = "moksorinw@gmail.com",
    [switch]$SkipTauri,
    [switch]$SkipBrowser,
    [switch]$SkipAnalyze
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
$no1kmediRoot = Join-Path $root "projects\no1kmedi"
$tauriEnv = Join-Path $root "projects\clinician-paste-chart-tauri\.env"
$localUrl = "http://127.0.0.1:3010/clinician?panel=gold"
$port = 3010
$sample = @"
김민수 / 1988-03-12 / 남 / 36세 / 요통 3주

[주소] 서울 강남
[CC] 요추부 통증, 3주 전부터 악화. 앉아 있을 때 더 아픔.
[Hx] 진통제 병력
"@

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

function Wait-HttpOk([string]$url, [int]$timeoutSec = 120) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    $attempt = 0
    while ((Get-Date) -lt $deadline) {
        $attempt++
        if (Test-HttpOk $url) {
            Write-Host "[paste-chart-auto] HTTP ready ($attempt) $url" -ForegroundColor DarkGray
            return
        }
        if ($attempt -eq 1 -or ($attempt % 5) -eq 0) {
            Write-Host "[paste-chart-auto] waiting for $url ... ($attempt)" -ForegroundColor DarkYellow
        }
        Start-Sleep -Seconds 2
    }
    throw "timeout waiting for $url"
}

function Sync-TauriLocalEnv {
    $lines = @()
    if (Test-Path $tauriEnv) { $lines = Get-Content $tauriEnv -Encoding UTF8 }
    $map = @{
        "KM_CLINICIAN_EMAIL" = $Email
        "KM_CLINICIAN_PASTE_CHART_URL" = $localUrl
    }
    foreach ($key in $map.Keys) {
        $val = $map[$key]
        $idx = [array]::FindIndex($lines, [Predicate[string]] { param($l) $l -match "^\s*$key\s*=" })
        if ($idx -ge 0) { $lines[$idx] = "$key=$val" } else { $lines += "$key=$val" }
    }
    Set-Content -Path $tauriEnv -Value $lines -Encoding UTF8
}

$probeUrl = "$localUrl"
$panelUrl = "$localUrl&email=$([uri]::EscapeDataString($Email))"

Write-Host "[paste-chart-auto] 1/5 env + clipboard" -ForegroundColor Cyan
Sync-TauriLocalEnv
Set-Clipboard -Value $sample

Write-Host "[paste-chart-auto] 2/5 ensure :$port dev server" -ForegroundColor Cyan
if (-not (Test-PortListening $port)) {
    if ($SkipTauri) {
        Write-Host "[paste-chart-auto] starting Next dev on :$port" -ForegroundColor Cyan
        Start-Process -FilePath "cmd.exe" -ArgumentList @(
            "/c", "cd /d `"$no1kmediRoot`" && npm run dev"
        ) -WindowStyle Minimized
    } else {
        Write-Host "[paste-chart-auto] starting Tauri dev (owns Next :$port via beforeDevCommand)" -ForegroundColor Cyan
        Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            (Join-Path $root "scripts\Invoke-ClinicianPasteChartTauriDev_v1.ps1")
        ) -WindowStyle Minimized
    }
} else {
    Write-Host "[paste-chart-auto] :$port already listening" -ForegroundColor DarkGray
}
Wait-HttpOk $probeUrl

if (-not $SkipAnalyze) {
    Write-Host "[paste-chart-auto] 3/5 API analyze + SOAP gate (no manual click)" -ForegroundColor Cyan
    $env:NO1KMEDI_BASE_URL = "http://127.0.0.1:$port"
    $env:KM_CLINICIAN_SMOKE_EMAIL = $Email
    Push-Location $no1kmediRoot
    try {
        node ./scripts/verify-paste-chart-auto-local-v1.mjs
        if ($LASTEXITCODE -ne 0) { throw "verify-paste-chart-auto-local failed exit $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[paste-chart-auto] 3/5 analyze skipped (-SkipAnalyze)" -ForegroundColor DarkYellow
}

if (-not $SkipTauri) {
    Write-Host "[paste-chart-auto] 4/5 Tauri offline gate" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Invoke-ClinicianPasteChartTauriAutoVerify_v1.ps1")
    if ($LASTEXITCODE -ne 0) { throw "Tauri auto verify failed exit $LASTEXITCODE" }
} else {
    Write-Host "[paste-chart-auto] 4/5 Tauri skipped (-SkipTauri)" -ForegroundColor DarkYellow
}

if (-not $SkipBrowser) {
    Write-Host "[paste-chart-auto] 5/5 open browser $panelUrl" -ForegroundColor Cyan
    Start-Process $panelUrl
} else {
    Write-Host "[paste-chart-auto] 5/5 browser skipped (-SkipBrowser)" -ForegroundColor DarkYellow
}

Write-Host "[paste-chart-auto] done — clipboard ready, Ctrl+V in omni or use Tauri hotkey" -ForegroundColor Green
