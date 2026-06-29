# Validate inbox exports then build B-track LoRA corpus JSONL (research_only · no auto train).
param(
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path (Join-Path $root "scripts\validate_personadiary_btrack_export_inbox_v1.py"))) {
    $root = Split-Path -Parent $PSScriptRoot
}

Push-Location $root
try {
    py scripts/validate_personadiary_btrack_export_inbox_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $corpusArgs = @("scripts/build_personadiary_btrack_lora_corpus_v1.py")
    if ($Strict) { $corpusArgs += "--strict" }
    py @corpusArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
