# One-click coding intent 3-point link record (research_only; B-track PoC).
param(
    [switch]$VerifyOnly,
    [switch]$IncludeDiff,
    [switch]$RunGate,
    [switch]$AllowPartial,
    [switch]$StrictVerify,
    [string]$MissionId,
    [string]$Note
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script = Join-Path $PSScriptRoot "record_coding_intent_link_v1.py"

if (-not (Test-Path -LiteralPath $script)) {
    throw "Missing: $script"
}

if ($VerifyOnly) {
    $args = @($script, "verify")
    if ($StrictVerify) { $args += "--strict" }
    & py @args
    exit $LASTEXITCODE
}

$args = @($script, "record")
if ($IncludeDiff) { $args += "--include-diff" }
if ($RunGate) { $args += "--run-gate" }
if ($AllowPartial) { $args += "--allow-partial" }
if ($MissionId) { $args += @("--mission-id", $MissionId) }
if ($Note) { $args += @("--note", $Note) }

Push-Location $root
try {
    & py @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
