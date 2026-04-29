# Generated 2026-04-29 — split pending workspace changes into 4 reviewable commits.
# Run from repo root:  pwsh -NoProfile -File reports/git_add_batches_pending.ps1 -Batch A
# Valid -Batch values: A | B | C | D | Submodule | List

param(
    [ValidateSet('A', 'B', 'C', 'D', 'Submodule', 'List')]
    [string]$Batch = 'List'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

function Invoke-BatchA_Code_Ci_Tests_Scripts {
    # CI, root scripts/tests, app source (no artifacts, no SSOT json dumps)
    git add .github/workflows/
    git add scripts/
    git add tests/
    git add projects/bitcoin-trading/src/
    # PS1 ops helpers only at this folder level (excludes jemaai-cloud-mvp/*.json)
    git add projects/bitcoin-trading/ops/windows-rehearsal/*.ps1
    git add projects/no1kmedi/package.json
    git add projects/no1kmedi/scripts/
    git add projects/no1kmedi/src/
}

function Invoke-BatchB_Artifacts_Reports_Data {
    git add docs/final/artifacts/
    git add reports/
    git add data/
    git add projects/bitcoin-trading/memory/
    git add projects/bitcoin-trading/exports/
    git add projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_public_bundle_v1.json
}

function Invoke-BatchC_Docs_Rules {
    git add docs/final/CENTRAL_AGENT_MEMORY_V1.md
    git add docs/final/CURRENT_OPS_SNAPSHOT.md
}

function Invoke-BatchD_Config {
    git add .vscode/settings.json
    git add projects/no1kmedi/.env.example
}

function Invoke-BatchSubmodule {
    git add projects/mkm/mkm-life
}

switch ($Batch) {
    'A' { Invoke-BatchA_Code_Ci_Tests_Scripts }
    'B' { Invoke-BatchB_Artifacts_Reports_Data }
    'C' { Invoke-BatchC_Docs_Rules }
    'D' { Invoke-BatchD_Config }
    'Submodule' { Invoke-BatchSubmodule }
    'List' {
        @'
# --- Batch A: code, CI, scripts, tests, app source (~155 paths) ---
git add .github/workflows/
git add scripts/
git add tests/
git add projects/bitcoin-trading/src/
git add projects/bitcoin-trading/ops/windows-rehearsal/*.ps1
git add projects/no1kmedi/package.json
git add projects/no1kmedi/scripts/
git add projects/no1kmedi/src/

# --- Batch B: artifacts, reports, data, memory/exports, showroom JSON (~338 paths) ---
git add docs/final/artifacts/
git add reports/
git add data/
git add projects/bitcoin-trading/memory/
git add projects/bitcoin-trading/exports/
git add projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_public_bundle_v1.json

# --- Batch C: handoff / memory MD (2 paths) ---
git add docs/final/CENTRAL_AGENT_MEMORY_V1.md
git add docs/final/CURRENT_OPS_SNAPSHOT.md

# --- Batch D: IDE + env example (2 paths) ---
git add .vscode/settings.json
git add projects/no1kmedi/.env.example

# --- Submodule pointer (1 path) — optional separate commit ---
git add projects/mkm/mkm-life
'@ | Write-Output
    }
}

if ($Batch -ne 'List') {
    Write-Host "Staged batch $Batch. Run: git status"
}
