# Build PR-range coding intent manifest (research_only).
param(
    [string]$Base,
    [string]$Note,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script = Join-Path $PSScriptRoot "build_coding_intent_pr_manifest_v1.py"

if (-not (Test-Path -LiteralPath $script)) {
    throw "Missing: $script"
}

$args = @($script)
if ($Base) { $args += @("--base", $Base) }
if ($Note) { $args += @("--note", $Note) }
if ($DryRun) { $args += "--dry-run" }

Push-Location $root
try {
    & py @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
