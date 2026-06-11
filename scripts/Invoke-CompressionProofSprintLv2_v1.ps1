# Proof Sprint Lv.3 — expand corpus + golden40 + handoff bench + reproduce pack
param(
    [switch]$SkipHandoff,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$root = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}
Set-Location $root

$py = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
$args = @('scripts/run_compression_evidence_lv1_chain_v1.py')
if ($SkipHandoff) { $args += '--skip-handoff' }

if ($WhatIf) {
    Write-Host ("plan: {0} {1}" -f $py, ($args -join ' '))
    exit 0
}

& $py @args
exit $LASTEXITCODE
