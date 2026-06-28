#Requires -Version 5.1
<#
.SYNOPSIS
  Non-blocking Tauri Paste Chart gate — offline smokes + cargo check + local dev markers.

.EXAMPLE
  powershell -File scripts\Invoke-ClinicianPasteChartTauriAutoVerify_v1.ps1
#>
param(
    [string]$ProjectRoot = "C:\workspace\projects\clinician-paste-chart-tauri"
)

$ErrorActionPreference = "Stop"

$cargoBin = Join-Path $env:USERPROFILE ".cargo\bin"
$cargoExe = Join-Path $cargoBin "cargo.exe"
if (-not (Test-Path $cargoExe)) {
    throw "cargo not found at $cargoExe — install Rust stable from https://rustup.rs/ then retry"
}
$env:PATH = "$cargoBin;$env:PATH"

function Assert-FileContains([string]$path, [string]$needle, [string]$label) {
    if (-not (Test-Path $path)) { throw "missing $path" }
    $text = Get-Content $path -Raw -Encoding UTF8
    if ($text -notmatch [regex]::Escape($needle)) {
        throw "$label missing marker: $needle"
    }
}

Push-Location $ProjectRoot
try {
    Write-Host "[paste-chart-tauri-verify] smoke:p22" -ForegroundColor Cyan
    npm run smoke:p22
    if ($LASTEXITCODE -ne 0) { throw "smoke:p22 failed exit $LASTEXITCODE" }

    Write-Host "[paste-chart-tauri-verify] smoke:scaffold" -ForegroundColor Cyan
    npm run smoke:scaffold
    if ($LASTEXITCODE -ne 0) { throw "smoke:scaffold failed exit $LASTEXITCODE" }

    Write-Host "[paste-chart-tauri-verify] cargo check" -ForegroundColor Cyan
    npm run check:rust
    if ($LASTEXITCODE -ne 0) { throw "cargo check failed exit $LASTEXITCODE" }

    $libRs = Join-Path $ProjectRoot "src-tauri\src\lib.rs"
    $conf = Join-Path $ProjectRoot "src-tauri\tauri.conf.json"
    Assert-FileContains $libRs "schedule_initial_clipboard_paste" "lib.rs auto paste"
    Assert-FileContains $libRs "embed=tauri" "lib.rs tauri embed query"
    Assert-FileContains $conf "127.0.0.1:3010/clinician?panel=gold" "tauri.conf local devUrl"

    Write-Host "[paste-chart-tauri-verify] OK" -ForegroundColor Green
} finally {
    Pop-Location
}
