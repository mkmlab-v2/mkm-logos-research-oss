[CmdletBinding()]
param(
    [string]$PythonExe = "py",
    [string]$StageProfile = "safe",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Invoke-Stage {
    param(
        [int]$Index,
        [string]$Lengths,
        [string]$OovRatios,
        [int]$SamplesCap
    )

    Write-Host ("[Stage {0}] lengths={1} oov={2} cap={3}" -f $Index, $Lengths, $OovRatios, $SamplesCap)
    $cmd = @(
        "scripts/run_trackb_top_combo_stress_grid.py",
        "--lengths", $Lengths,
        "--oov-ratios", $OovRatios,
        "--samples-per-cell-cap", "$SamplesCap"
    )

    if ($DryRun) {
        Write-Host ("[DryRun] {0} {1}" -f $PythonExe, ($cmd -join " "))
        return
    }

    & $PythonExe @cmd
    if ($LASTEXITCODE -ne 0) {
        throw "Stage $Index failed with exit code $LASTEXITCODE"
    }
}

switch ($StageProfile.ToLowerInvariant()) {
    "safe" {
        # Default for unstable environments: start small and expand.
        Invoke-Stage -Index 1 -Lengths "20,24" -OovRatios "0.1,0.2" -SamplesCap 1
        Invoke-Stage -Index 2 -Lengths "64,128,256,512" -OovRatios "0.0,0.1,0.2,0.3" -SamplesCap 2
        Invoke-Stage -Index 3 -Lengths "64,128,256,512,1024" -OovRatios "0.0,0.1,0.2,0.3,0.4" -SamplesCap 4
    }
    "extended" {
        Invoke-Stage -Index 1 -Lengths "20,24" -OovRatios "0.1,0.2" -SamplesCap 1
        Invoke-Stage -Index 2 -Lengths "64,128,256,512" -OovRatios "0.0,0.1,0.2,0.3" -SamplesCap 3
        Invoke-Stage -Index 3 -Lengths "64,128,256,512,1024" -OovRatios "0.0,0.1,0.2,0.3,0.4" -SamplesCap 6
        Invoke-Stage -Index 4 -Lengths "64,128,256,512,1024,2048" -OovRatios "0.0,0.1,0.2,0.3,0.4,0.5" -SamplesCap 8
    }
    default {
        throw "Unsupported StageProfile '$StageProfile'. Use safe|extended."
    }
}

Write-Host "[Done] staged stress-grid run completed."
