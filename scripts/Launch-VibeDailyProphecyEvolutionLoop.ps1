<#
.SYNOPSIS
  Launcher for scheduled-task / minimal-PATH environments (ensures py/python resolve).

.DESCRIPTION
  Task Scheduler often runs with a stripped PATH. Prepend %SystemRoot% (for py.exe)
  and the active Python install prefix (via py -c) before delegating to the daily loop.
#>
param(
    [int]$RunsPerPrompt = 10,
    [switch]$StrictCoverageGate
)

$ErrorActionPreference = "Stop"

# py.exe lives under System32; ensure Windows directory is searchable.
if ($env:Path -notlike "*$env:SystemRoot*") {
    $env:Path = "$env:SystemRoot;$env:Path"
}

# Prepend active Python directories when PATH is minimal (Task Scheduler).
try {
    $prefix = & py -c "import sys; print(sys.prefix)" 2>$null
    if ($prefix) {
        $prefix = $prefix.Trim()
        $scripts = Join-Path $prefix "Scripts"
        $prepend = @($prefix)
        if (Test-Path -LiteralPath $scripts) {
            $prepend += $scripts
        }
        foreach ($p in $prepend) {
            if ($env:Path -notlike "*$p*") {
                $env:Path = "$p;$env:Path"
            }
        }
    }
} catch {
    # If py is unavailable here, the child script will surface the error with exit code.
}

$runner = Join-Path $PSScriptRoot "run_vibe_daily_prophecy_evolution_loop_v1.ps1"
& $runner @PSBoundParameters
exit $LASTEXITCODE
