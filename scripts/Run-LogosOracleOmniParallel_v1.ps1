# Omni-parallel: CDIM + OL GraphRAG bridge + Chronology eval (3 job tracks).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosOracleOmniParallel_v1.ps1
param(
    [switch]$SkipChronology,
    [switch]$SkipOlBridge,
    [switch]$SkipCdim,
    [switch]$SkipChronologyBundle,
    [switch]$SkipChronologyPytest,
    [switch]$CdimSkipLens,
    [switch]$MirrorShowroomCdim
)

$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "C:\workspace" }
Set-Location -LiteralPath $root

$trackCdim = {
    Set-Location $using:root
    $skipLens = $using:CdimSkipLens
    $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\Run-LogosCrossDomainInterfaceParallel_v1.ps1", "-Validate")
    if ($skipLens) { $args += "-SkipLens" }
    & powershell @args
    if ($LASTEXITCODE -ne 0) { throw "CDIM track" }
}

$trackOl = {
    Set-Location $using:root
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosOlGraphBridgeParallel_v1.ps1
    if ($LASTEXITCODE -ne 0) { throw "OL bridge track" }
}

$trackChr = {
    Set-Location $using:root
    $bundle = $using:SkipChronologyBundle
    $pytest = $using:SkipChronologyPytest
    $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\Run-LogosChronologyAllParallel_v1.ps1")
    if ($bundle) { $args += "-SkipBundle" }
    if ($pytest) { $args += "-SkipPytest" }
    & powershell @args
    if ($LASTEXITCODE -ne 0) { throw "Chronology track" }
}

$jobs = @()
if (-not $SkipCdim) { $jobs += Start-Job -Name CDIM -ScriptBlock $trackCdim }
if (-not $SkipOlBridge) { $jobs += Start-Job -Name OLBridge -ScriptBlock $trackOl }
if (-not $SkipChronology) { $jobs += Start-Job -Name Chronology -ScriptBlock $trackChr }

if ($jobs.Count -gt 0) {
    Write-Host "[omni] phase 1: $($jobs.Count) track(s) in parallel" -ForegroundColor Cyan
    $jobs | Wait-Job | Out-Null
    foreach ($j in $jobs) {
        if ($j.State -eq "Failed") {
            Receive-Job -Job $j -ErrorAction SilentlyContinue | Write-Host
            throw "Job $($j.Name) failed"
        }
        Receive-Job -Job $j | Write-Host
        Remove-Job -Job $j
    }
}

Write-Host "[omni] phase 2: showroom CDIM slice + Track C dashboard" -ForegroundColor Cyan
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
& $py scripts/build_showroom_cdim_slice_v1.py $(if ($MirrorShowroomCdim) { "--mirror-staging" })
if ($LASTEXITCODE -ne 0) { throw "showroom cdim slice" }
& $py scripts/build_mkm_trackc_ops_dashboard_v1.py
if ($LASTEXITCODE -ne 0) { throw "trackc dashboard" }

Write-Host "[omni] phase 3: smoke pytest (cdim + concept bridge)" -ForegroundColor Cyan
& $py -m pytest tests/test_logos_cross_domain_interface_v1.py tests/test_build_showroom_cdim_slice_v1.py tests/test_logos_concept_bridge_v1.py -q --tb=line
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: Logos Oracle omni-parallel complete" -ForegroundColor Green
