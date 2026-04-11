# One-shot local demo: V1 stub (8010) + V2 stub (8011) + static server (8765) + default browser.
# Stubs run in separate minimized windows; close them when done. Not for production.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Start-CompressionV2ExplorerDemo.ps1
#   -WhatIf   # print only

param(
    [switch]$WhatIf,
    [int]$StaticPort = 8765
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

function Invoke-DemoProcess {
    param([string]$Name, [string[]]$ArgumentList)
    if ($WhatIf) {
        Write-Host "[WhatIf] $Name : py $($ArgumentList -join ' ')" -ForegroundColor Yellow
        return
    }
    Start-Process -FilePath "py" -ArgumentList $ArgumentList -WorkingDirectory $workspaceRoot -WindowStyle Minimized
}

Write-Host "=== Compression V1/V2 Explorer demo (local stubs) ===" -ForegroundColor Cyan
Invoke-DemoProcess "V1 token API stub :8010" @(
    "-m", "uvicorn", "scripts.compression_token_api_stub:app", "--host", "127.0.0.1", "--port", "8010"
)
Start-Sleep -Milliseconds 400
Invoke-DemoProcess "V2 Trust Packet stub :8011" @(
    "-m", "uvicorn", "scripts.compression_token_api_v2_stub:app", "--host", "127.0.0.1", "--port", "8011"
)
Start-Sleep -Milliseconds 400
$mvp = Join-Path $workspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp"
if ($WhatIf) {
    Write-Host "[WhatIf] static http.server $StaticPort in $mvp" -ForegroundColor Yellow
} else {
    Start-Process -FilePath "py" -ArgumentList @("-m", "http.server", "$StaticPort", "--bind", "127.0.0.1") `
        -WorkingDirectory $mvp -WindowStyle Minimized
}
Start-Sleep -Seconds 1
$url = "http://127.0.0.1:$StaticPort/compression_v2_explorer.html"
if ($WhatIf) {
    Write-Host "[WhatIf] Start-Process browser $url" -ForegroundColor Yellow
} else {
    Start-Process $url
    Write-Host "Opened $url — use Live API mode (V1 8010 / V2 8011)." -ForegroundColor Green
}
Write-Host "Stop: close the three minimized py windows or end uvicorn/http.server processes." -ForegroundColor DarkGray
