# Build docs/final/artifacts/prophecy_two_track_snapshot_v1_latest.json (two-track boundary snapshot).
# Run from repo root.

$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
Set-Location -LiteralPath $root
& py "scripts/build_prophecy_two_track_snapshot_v1.py" @args
exit $LASTEXITCODE
