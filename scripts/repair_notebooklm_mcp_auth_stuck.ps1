param(
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"

$profileRoot = Join-Path $env:LOCALAPPDATA "notebooklm-mcp\Data\chrome_profile"

Write-Host "=== Repair NotebookLM MCP auth stuck state ===" -ForegroundColor Cyan
Write-Host "Profile root: $profileRoot"

if (-not (Test-Path $profileRoot)) {
    Write-Host "Profile root does not exist yet. Nothing to repair." -ForegroundColor Yellow
    exit 0
}

$targets = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -eq "chrome.exe" -and
        $_.CommandLine -match "notebooklm-mcp\\Data\\chrome_profile"
    }

if ($targets.Count -gt 0) {
    $ids = $targets | Select-Object -ExpandProperty ProcessId
    Write-Host ("Detected NotebookLM MCP Chrome processes: " + ($ids -join ", ")) -ForegroundColor Yellow
    if (-not $WhatIfOnly) {
        foreach ($p in $targets) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Write-Host "Killed NotebookLM MCP Chrome processes." -ForegroundColor Green
    } else {
        Write-Host "WhatIfOnly: skip killing processes." -ForegroundColor DarkGray
    }
} else {
    Write-Host "No NotebookLM MCP Chrome process found." -ForegroundColor Green
}

$lockCandidates = @(
    "lockfile",
    "SingletonLock",
    "SingletonCookie",
    "SingletonSocket"
) | ForEach-Object { Join-Path $profileRoot $_ }

foreach ($lockPath in $lockCandidates) {
    if (Test-Path $lockPath) {
        if (-not $WhatIfOnly) {
            Remove-Item -Force $lockPath -ErrorAction SilentlyContinue
            Write-Host "Removed lock artifact: $lockPath" -ForegroundColor Green
        } else {
            Write-Host "WhatIfOnly: would remove $lockPath" -ForegroundColor DarkGray
        }
    }
}

Write-Host ""
Write-Host "Next step:" -ForegroundColor Cyan
Write-Host "1) Retry NotebookLM MCP setup_auth"
Write-Host "2) Verify via get_health (authenticated=true)"
