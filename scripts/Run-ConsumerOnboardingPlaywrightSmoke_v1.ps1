# Consumer onboarding Playwright smoke — mkmlife + personadiary (local dev).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$mkmlifeUrl = if ($env:MKMLIFE_BASE_URL) { $env:MKMLIFE_BASE_URL } else { "http://127.0.0.1:3105" }
$no1kUrl = if ($env:NO1KMEDI_DEV_URL) { $env:NO1KMEDI_DEV_URL } else { "http://127.0.0.1:3010" }

function Stop-Port([int]$Port) {
    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
}

function Test-DevOk([string]$Url) {
    try {
        $r = Invoke-WebRequest -Uri $Url -TimeoutSec 20 -UseBasicParsing
        if ($r.StatusCode -ge 500) { return $false }
        if ($r.Content -like '*"statusCode":500*') { return $false }
        return $true
    } catch {
        return $false
    }
}

function Start-DevIfNeeded([string]$Name, [string]$WorkDir, [int]$Port, [string]$ProbePath) {
    $url = "http://127.0.0.1:$Port$ProbePath"
    if (Test-DevOk $url) { return }
    Write-Host "[onboarding-smoke] restarting $Name on $Port..." -ForegroundColor Yellow
    Stop-Port $Port
    Start-Sleep -Seconds 2
    $next = Join-Path $WorkDir ".next"
    if (Test-Path -LiteralPath $next) {
        Remove-Item -LiteralPath $next -Recurse -Force -ErrorAction SilentlyContinue
    }
    Start-Process -FilePath "npm" -ArgumentList @("run", "dev") -WorkingDirectory $WorkDir -WindowStyle Minimized
    $deadline = (Get-Date).AddSeconds(150)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 4
        if (Test-DevOk $url) { return }
    }
    Write-Error "$Name dev not healthy at $url after wait"
}

$mkmlifeDir = Join-Path $root "projects\mkm\mkm-life"
$no1kDir = Join-Path $root "projects\no1kmedi"
$env:MKM_WORKSPACE_ROOT = $root

Start-DevIfNeeded -Name "mkmlife" -WorkDir $mkmlifeDir -Port 3105 -ProbePath "/onboarding"
Start-DevIfNeeded -Name "no1kmedi" -WorkDir $no1kDir -Port 3010 -ProbePath "/personadiary/ops"

$env:MKMLIFE_BASE_URL = $mkmlifeUrl
$env:NO1KMEDI_DEV_URL = $no1kUrl
& node (Join-Path $root "scripts\smoke_consumer_onboarding_playwright_v1.mjs")
exit $LASTEXITCODE
