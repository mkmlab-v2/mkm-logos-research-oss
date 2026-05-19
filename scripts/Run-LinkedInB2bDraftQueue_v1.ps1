# LinkedIn B2B draft queue — assemble-only default (no API cost).
param(
    [string]$QueuePath = "",
    [string]$ItemId = "",
    [switch]$Gemini,
    [switch]$WithChart,
    [switch]$InitFromExample,
    [switch]$DryRun,
    [switch]$StrictCompliance
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root "scripts\generate_linkedin_b2b_copy_v1.py"
$args = @($py)
if ($QueuePath) { $args += @("--queue", $QueuePath) }
if ($ItemId) { $args += @("--item-id", $ItemId) }
if ($InitFromExample) { $args += "--init-from-example" }
if ($DryRun) { $args += "--dry-run"; & py @args; exit $LASTEXITCODE }
if ($Gemini) { $args += "--gemini" } else { $args += "--assemble-only" }
if ($WithChart) { $args += "--with-chart" }
if ($StrictCompliance) { $args += "--strict-compliance" }
& py @args
exit $LASTEXITCODE
