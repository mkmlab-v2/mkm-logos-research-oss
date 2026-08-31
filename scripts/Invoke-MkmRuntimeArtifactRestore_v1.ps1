# Restore runtime-only artifact noise (timestamp drift) — no push
param(
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..

$targets = @(
    'docs/final/artifacts',
    'reports'
)

$restored = @()
foreach ($t in $targets) {
    if (-not (Test-Path $t)) { continue }
    $modified = git diff --name-only -- $t 2>$null
    foreach ($f in $modified) {
        if ($f -match '_latest\.(json|md|jsonl)$' -or $f -match 'reports/.*_latest\.') {
            if ($WhatIf) {
                Write-Host "[WhatIf] restore $f"
            } else {
                git restore -- $f
            }
            $restored += $f
        }
    }
}

Write-Host "restored_count=$($restored.Count)"
if ($WhatIf) { Write-Host 'WhatIf only — no files changed' }
