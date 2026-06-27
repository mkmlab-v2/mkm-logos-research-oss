#Requires -Version 5.1
<#
.SYNOPSIS
  Launch clinician-paste-chart-tauri dev (MSVC + .env).

.EXAMPLE
  powershell -File scripts\Invoke-ClinicianPasteChartTauriDev_v1.ps1
#>
param(
    [string]$ProjectRoot = "C:\workspace\projects\clinician-paste-chart-tauri"
)

$ErrorActionPreference = "Stop"
$vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw "vswhere missing — install VS Build Tools with C++ workload" }
$vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsPath) { throw "VC Tools not found — run vs_buildtools with Microsoft.VisualStudio.Workload.VCTools" }

$vcvars = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path $vcvars)) { throw "missing $vcvars" }

$cargoBin = Join-Path $env:USERPROFILE ".cargo\bin"
$cargoExe = Join-Path $cargoBin "cargo.exe"
if (-not (Test-Path $cargoExe)) {
    throw "cargo not found at $cargoExe — install Rust stable from https://rustup.rs/ then retry"
}

Write-Host "[paste-chart-tauri] dev from $ProjectRoot" -ForegroundColor Cyan
cmd /c "`"$vcvars`" && set PATH=%USERPROFILE%\.cargo\bin;%PATH% && cd /d `"$ProjectRoot`" && npm run dev"
if ($LASTEXITCODE -ne 0) { throw "tauri dev failed exit $LASTEXITCODE" }
