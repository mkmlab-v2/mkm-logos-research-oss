#Requires -Version 5.1
<#
.SYNOPSIS
  Fully automated Paste Chart local loop: HMR dev + clipboard + API analyze + browser.

.EXAMPLE
  powershell -File scripts\Invoke-ClinicianPasteChartAutoDev_v1.ps1
#>
param(
    [string]$Email = "moksorinw@gmail.com",
    [switch]$SkipTauri,
    [switch]$SkipBrowser,
    [switch]$SkipAnalyze
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
$tauriEnv = Join-Path $root "projects\clinician-paste-chart-tauri\.env"
$localUrl = "http://127.0.0.1:3010/clinician?panel=gold"
$sample = @"
김민수 / 1988-03-12 / 남 / 36세 / 요통 3주

[주소] 서울 강남
[CC] 요추부 통증, 3주 전부터 악화. 앉아 있을 때 더 아픔.
[Hx] 진통제 병력
"@

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

Write-Host "[paste-chart-auto] 1/4 local Next + browser" -ForegroundColor Cyan
$hotArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "$root\scripts\Invoke-ClinicianPasteChartLocalHotReload_v1.ps1", "-Email", $Email)
if ($SkipBrowser) { $hotArgs += "-OpenOnly" }
& powershell @hotArgs

Sync-TauriLocalEnv
Set-Clipboard -Value $sample
Write-Host "[paste-chart-auto] 2/4 clipboard sample ready (Ctrl+V in omni)" -ForegroundColor DarkGray

if (-not $SkipAnalyze) {
    Write-Host "[paste-chart-auto] 3/4 API analyze + SOAP gate (no manual click)" -ForegroundColor Cyan
    $env:NO1KMEDI_BASE_URL = "http://127.0.0.1:3010"
    $env:KM_CLINICIAN_SMOKE_EMAIL = $Email
    Push-Location (Join-Path $root "projects\no1kmedi")
    try {
        node ./scripts/verify-paste-chart-auto-local-v1.mjs
        if ($LASTEXITCODE -ne 0) { throw "verify-paste-chart-auto-local failed exit $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[paste-chart-auto] 3/4 analyze skipped (-SkipAnalyze)" -ForegroundColor DarkYellow
}

if ($SkipTauri) {
    Write-Host "[paste-chart-auto] 4/4 done (browser + auto analyze). Paste Ctrl+V -> optional UI check." -ForegroundColor Green
    exit 0
}

Write-Host "[paste-chart-auto] 4/4 Tauri dev (local webview)" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File "$root\scripts\Invoke-ClinicianPasteChartTauriDev_v1.ps1"
