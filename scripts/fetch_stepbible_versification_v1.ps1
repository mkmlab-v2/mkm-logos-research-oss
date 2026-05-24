# Sparse-clone STEPBible-Data (Versification cone only) for MT↔BHS verse mapping research.
# Does not auto-ingest; run build scripts after clone. B-track / [HYPO] only.

param(
    [string]$StagingRoot = "C:\workspace\vault\external_lexicon",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
$repoUrl = "https://github.com/STEPBible/STEPBible-Data.git"
$targetDir = Join-Path $StagingRoot "sources\stepbible-data"
$lp = @("-c", "core.longpaths=true")

function Ensure-Directory([string]$PathValue) {
    if (-not (Test-Path -LiteralPath $PathValue)) {
        New-Item -ItemType Directory -Path $PathValue -Force | Out-Null
    }
}

if (Test-Path -LiteralPath $targetDir) {
    Write-Host "STEPBible-Data already present: $targetDir"
    Write-Host "To refresh Versification only: remove folder and re-run, or git pull in that directory."
    exit 0
}

$parent = Split-Path -Parent $targetDir
Ensure-Directory $parent

Write-Host "Cloning STEPBible-Data (sparse: Versification) ..."
& git @lp clone --filter=blob:none --sparse $repoUrl $targetDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Push-Location $targetDir
try {
    & git @lp sparse-checkout init --cone
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & git @lp sparse-checkout set Versification
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}

Write-Host "Done. Versification path: $targetDir\Versification"

if (-not $SkipPush) {
    & "C:\workspace\scripts\push_external_lexicon_to_vault.ps1" -SourceRoot $StagingRoot
}
