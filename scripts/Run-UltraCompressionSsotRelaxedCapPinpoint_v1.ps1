# B-track: ssot relaxed cap 0.45 pinpoint — never writes Track A active.
param(
    [switch]$DryRun,
    [string]$OutJson = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$argsList = @()
if ($DryRun) { $argsList += "--dry-run" }
if ($OutJson) { $argsList += @("--out-json", $OutJson) }
& py (Join-Path $root "scripts\run_ultra_compression_ssot_relaxed_cap_pinpoint_v1.py") @argsList
exit $LASTEXITCODE
