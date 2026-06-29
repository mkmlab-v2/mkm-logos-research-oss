# Ko shorts Cursor IDE QA — programmatic + optional localhost preview (no CapCut/Vrew).

#

# Default: generate QA + disk health only (no background http.server).

#

# Usage:

#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-KoShortsCursorIdeQa_v1.ps1

#   powershell -File scripts\Invoke-KoShortsCursorIdeQa_v1.ps1 -StartServer

#   powershell -File scripts\Invoke-KoShortsCursorIdeQa_v1.ps1 -StartServer -CleanupPortOnExit

#   powershell -File scripts\Invoke-KoShortsCursorIdeQa_v1.ps1 -CleanupPort

#

param(

    [int]$Port = 8796,

    [switch]$StartServer,

    [switch]$CleanupPort,

    [switch]$CleanupPortOnExit,

    [switch]$BrowserSmoke,

    [switch]$StrictBrowser

)



$ErrorActionPreference = 'Stop'

$Root = Split-Path $PSScriptRoot -Parent

Set-Location $Root



$StartedServer = $false

$ServerPidFile = Join-Path $Root 'reports/.ko_shorts_preview_server_v1.pid'



function Write-Step([string]$Msg) { Write-Host "==> $Msg" -ForegroundColor Cyan }



function Stop-PreviewServerIfOwned {

    if (-not (Test-Path -LiteralPath $ServerPidFile)) { return }

    $pidText = (Get-Content -LiteralPath $ServerPidFile -Raw).Trim()

    if ($pidText -match '^\d+$') {

        $ownedPid = [int]$pidText

        if (Get-Process -Id $ownedPid -ErrorAction SilentlyContinue) {

            Stop-Process -Id $ownedPid -Force -ErrorAction SilentlyContinue

            Write-Host "Stopped owned preview server PID $ownedPid" -ForegroundColor DarkGray

        }

    }

    Remove-Item -LiteralPath $ServerPidFile -Force -ErrorAction SilentlyContinue

}



if ($CleanupPort) {

    Write-Step 'Stop-KoShortsPreviewServer_v1.ps1'

    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Stop-KoShortsPreviewServer_v1.ps1 -Port $Port

}



try {

    Write-Step 'run_ko_shorts_cursor_ide_qa_v1.py'

    & py scripts/run_ko_shorts_cursor_ide_qa_v1.py --port $Port

    if ($LASTEXITCODE -ne 0) { throw "cursor ide qa exit $LASTEXITCODE" }



    $reportPath = Join-Path $Root 'reports/ko_shorts_cursor_ide_qa_v1_latest.json'

    $report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json

    $previewUrl = $report.preview_url



    if ($StartServer) {

        $existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

        if (-not $existing) {

            Write-Step "http.server $Port (reports/)"

            $proc = Start-Process -FilePath 'py' -ArgumentList @(

                '-m', 'http.server', "$Port", '--bind', '127.0.0.1', '--directory', 'reports'

            ) -WorkingDirectory $Root -WindowStyle Minimized -PassThru

            $proc.Id | Set-Content -LiteralPath $ServerPidFile -Encoding ascii -NoNewline

            $StartedServer = $true

            Start-Sleep -Seconds 1

        } else {

            Write-Host "port $Port already listening (reuse)" -ForegroundColor DarkGray

        }

    }



    Write-Step 'check_ko_shorts_preview_health_v1.py (disk)'

    & py scripts/check_ko_shorts_preview_health_v1.py --port $Port

    if ($LASTEXITCODE -ne 0) { throw "preview disk health exit $LASTEXITCODE" }



    if ($StartServer) {

        Write-Step 'check_ko_shorts_preview_health_v1.py (require-http)'

        & py scripts/check_ko_shorts_preview_health_v1.py --port $Port --require-http

        if ($LASTEXITCODE -ne 0) { throw "preview http health exit $LASTEXITCODE" }

    }



    Write-Step 'check_cursor_ide_browser_readiness_v1.ps1'

    $browserArgs = @('-File', 'scripts/check_cursor_ide_browser_readiness_v1.ps1')

    if ($StrictBrowser) { $browserArgs += '-Strict' }

    & powershell -NoProfile -ExecutionPolicy Bypass @browserArgs

    $browserReady = ($LASTEXITCODE -eq 0)



    Write-Host ""

    if ($StartServer) {

        Write-Host "Preview URL (HTTP verified): $previewUrl" -ForegroundColor Green

    } else {

        Write-Host "Preview file: reports/ko_shorts_cursor_preview_v1.html (disk OK; server OFF)" -ForegroundColor Green

        Write-Host "Live preview: re-run with -StartServer" -ForegroundColor DarkGray

    }

    Write-Host "Agent flow: browser_navigate -> browser_lock -> browser_snapshot -> unlock" -ForegroundColor DarkGray

    Write-Host "Artifacts: reports/ko_shorts_cursor_ide_qa_v1_latest.json" -ForegroundColor DarkGray



    if ($BrowserSmoke) {

        if (-not $browserReady) {

            Write-Host 'Browser readiness not strict-pass; enable Browser in Cursor or use -StartServer.' -ForegroundColor Yellow

        } elseif (-not $StartServer) {

            Write-Host 'BrowserSmoke needs -StartServer for localhost fetch.' -ForegroundColor Yellow

        } else {

            Write-Host 'BrowserSmoke: use browser_navigate in agent chat to open preview URL.' -ForegroundColor Yellow

        }

    }



    Write-Host 'OK: Invoke-KoShortsCursorIdeQa_v1' -ForegroundColor Green

    exit 0

}

finally {

    if ($CleanupPortOnExit -and $StartedServer) {

        Stop-PreviewServerIfOwned

    }

}

