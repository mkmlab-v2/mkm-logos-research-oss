# B-track: low-saving / hit_count=0 local cap sweep (RQ-016 A-plan). Never writes Track A active.
param(
    [switch]$DryRun,
    [string]$OutJson = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = "py"
$script = Join-Path $root "scripts\run_compression_low_saving_local_cap_sweep_v1.py"
$argsList = @()
if ($DryRun) { $argsList += "--dry-run" }
if ($OutJson) { $argsList += @("--out-json", $OutJson) }
& $py $script @argsList
exit $LASTEXITCODE
