param(
    [switch]$WhatIfOnly,
    [int]$StaleNodeMaxHours = 12
)

$ErrorActionPreference = "Stop"

$profileRoot = Join-Path $env:LOCALAPPDATA "notebooklm-mcp\Data\chrome_profile"

Write-Host "=== Repair NotebookLM MCP auth stuck state ===" -ForegroundColor Cyan
Write-Host "Profile root      : $profileRoot"
Write-Host "Stale node cutoff : ${StaleNodeMaxHours}h"

# --- 1) Stop chrome.exe instances bound to NotebookLM MCP profile ---
if (-not (Test-Path $profileRoot)) {
    Write-Host "Profile root does not exist yet. Skipping chrome scan." -ForegroundColor Yellow
} else {
    $chromeTargets = @(Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -eq "chrome.exe" -and
            $_.CommandLine -match "notebooklm-mcp\\Data\\chrome_profile"
        })

    if (@($chromeTargets).Count -gt 0) {
        $ids = $chromeTargets | Select-Object -ExpandProperty ProcessId
        Write-Host ("Detected NotebookLM MCP Chrome processes: " + ($ids -join ", ")) -ForegroundColor Yellow
        if (-not $WhatIfOnly) {
            foreach ($p in $chromeTargets) {
                Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            }
            Write-Host "Killed NotebookLM MCP Chrome processes." -ForegroundColor Green
        } else {
            Write-Host "WhatIfOnly: skip killing chrome processes." -ForegroundColor DarkGray
        }
    } else {
        Write-Host "No NotebookLM MCP Chrome process found." -ForegroundColor Green
    }

    # --- 1b) Clean up SingletonLock / lockfile artifacts ---
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
}

# --- 2) Stop stale notebooklm-mcp NODE / parent CMD processes (>= StaleNodeMaxHours) ---
$cutoff = (Get-Date).AddHours(-1 * $StaleNodeMaxHours)
$serverTargets = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*notebooklm-mcp*' -and
    ($_.Name -in @('node.exe','cmd.exe')) -and
    ($_.CreationDate -lt $cutoff)
})

if (@($serverTargets).Count -gt 0) {
    $ids = $serverTargets | ForEach-Object { "$($_.ProcessId)/$($_.Name)" }
    Write-Host ("Detected stale notebooklm-mcp processes (>${StaleNodeMaxHours}h): " + ($ids -join ", ")) -ForegroundColor Yellow
    if (-not $WhatIfOnly) {
        foreach ($p in $serverTargets) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Write-Host "Killed stale notebooklm-mcp processes." -ForegroundColor Green
    } else {
        Write-Host "WhatIfOnly: skip killing stale notebooklm-mcp processes." -ForegroundColor DarkGray
    }
} else {
    Write-Host "No stale notebooklm-mcp node/cmd processes (>${StaleNodeMaxHours}h)." -ForegroundColor Green
}

Write-Host ""
Write-Host "Next step:" -ForegroundColor Cyan
Write-Host "1) In Cursor: Settings -> MCP -> notebooklm toggle off/on (forces fresh handshake)"
Write-Host "2) Open a NEW chat (tool catalog is decided at chat start)"
Write-Host "3) In that chat: notebooklm.setup_auth -> notebooklm.get_health (authenticated=true)"
exit 0
