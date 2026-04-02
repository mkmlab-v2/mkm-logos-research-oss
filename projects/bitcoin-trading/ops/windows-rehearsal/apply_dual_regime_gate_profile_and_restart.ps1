param(
    [ValidateSet("conservative", "balanced", "aggressive")]
    [string]$Profile = "balanced",
    [switch]$PersistUserEnv,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

$switchScript = Join-Path $PSScriptRoot "switch_dual_regime_gate_profile.ps1"
$ensureScript = Join-Path $PSScriptRoot "ensure_daemon_running.ps1"

if (-not (Test-Path $switchScript)) {
    throw "Missing switch script: $switchScript"
}
if (-not (Test-Path $ensureScript)) {
    throw "Missing ensure script: $ensureScript"
}

Write-Host ("[gate-profile] target={0} persist={1} whatif={2}" -f $Profile, [bool]$PersistUserEnv, [bool]$WhatIf)

if ($WhatIf) {
    if ($PersistUserEnv) {
        Write-Host ("[whatif] Would run: {0} -Profile {1} -PersistUserEnv" -f $switchScript, $Profile)
    } else {
        Write-Host ("[whatif] Would run: {0} -Profile {1}" -f $switchScript, $Profile)
    }
} else {
    if ($PersistUserEnv) {
        & $switchScript -Profile $Profile -PersistUserEnv
    } else {
        & $switchScript -Profile $Profile
    }
}

# Restart singleton entrypoint so running process picks up new env.
$daemonProcs = Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -and
        ($_.CommandLine -match "start_24h_daemon\.py") -and
        ($_.Name -ne "py.exe")
    }

if (-not $daemonProcs -or @($daemonProcs).Count -eq 0) {
    Write-Host "[gate-profile] No running start_24h_daemon.py process found."
} else {
    foreach ($p in @($daemonProcs)) {
        if ($WhatIf) {
            Write-Host ("[whatif] Would stop PID={0} ({1})" -f $p.ProcessId, $p.Name)
        } else {
            Write-Host ("[gate-profile] Stopping PID={0} ({1})" -f $p.ProcessId, $p.Name)
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
}

if ($WhatIf) {
    Write-Host ("[whatif] Would run: {0}" -f $ensureScript)
} else {
    & $ensureScript
}

Write-Host "[gate-profile] done."

