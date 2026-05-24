#Requires -Version 5.1
<#
.SYNOPSIS
  Parallel B-track chronology + macro + resonance (HYPO only).
#>
$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "C:\workspace" }
Set-Location $root
$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "py" }
$warn = @()

function Step-Ok {
    param([string]$Name, [scriptblock]$Block, [switch]$WarnOnly)
    Write-Host "== $Name ==" -ForegroundColor Cyan
    & $Block
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        if ($WarnOnly) {
            Write-Host "WARN $Name exit=$code" -ForegroundColor Yellow
            $script:warn += "$Name exit=$code"
            return
        }
        throw "$Name failed exit=$code"
    }
    Write-Host "OK $Name" -ForegroundColor Green
}

Step-Ok "macro_news_adapters" { & $py scripts/build_btrack_news_macro_lens_adapters_v1.py }
Step-Ok "chronology_regime_match" { & $py scripts/build_chronology_regime_match_v1.py }
Step-Ok "logos_regime_resonance_shadow" -WarnOnly {
    & $py scripts/build_logos_regime_resonance_shadow_signal_v1.py
}
Step-Ok "chronology_match_pytest" {
    & $py -m pytest tests/test_build_chronology_regime_match_v1.py -q
}

$summary = @{
    schema = "chronology_btrack_parallel_v1"
    completed_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    warnings = $warn
    artifacts = @(
        "reports/constitution/btrack_pilot/chronology_regime_match_v1_latest.json"
        "docs/final/artifacts/macro_independent_lens_latest.json"
        "docs/final/artifacts/news_independent_lens_latest.json"
    )
}
$outJson = Join-Path $root "reports/parallel_chronology_btrack_latest.json"
New-Item -ItemType Directory -Force -Path (Split-Path $outJson) | Out-Null
$summary | ConvertTo-Json -Depth 6 | Set-Content -Path $outJson -Encoding UTF8
if ($warn.Count -gt 0) {
    Write-Host "DONE with warnings: $($warn -join '; ')" -ForegroundColor Yellow
    exit 0
}
Write-Host "Chronology B-track parallel OK" -ForegroundColor Green
exit 0
