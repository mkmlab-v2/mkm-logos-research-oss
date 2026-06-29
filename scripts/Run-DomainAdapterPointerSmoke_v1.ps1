# Domain adapter pointer smoke — sync_bridge + ops memory overlay + offline gates.
# Pointers: docs/final/artifacts/mkm_ops_sync_bridge_v1.json domain_adapters
# Usage: pwsh -NoProfile -File scripts\Run-DomainAdapterPointerSmoke_v1.ps1 [-SkipPixelGate] [-SkipAudioPytest]

param(
    [switch]$SkipPixelGate,
    [switch]$SkipAudioPytest
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

Write-Host "`n=== [0/6] pixel materialize + local sprite paths ===" -ForegroundColor Cyan
& py scripts/materialize_mkmlife_pixel_sprites_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & py scripts/apply_mkmlife_pixel_language_local_sprite_paths_v1.py --mode local
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & py scripts/check_mkmlife_pixel_sprite_deploy_mode_v1.py --expect local

Write-Host "`n=== [1/6] sync_bridge domain_adapters pointer gate ===" -ForegroundColor Cyan
& py scripts/check_mkm_ops_sync_bridge_domain_adapters_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== [2/6] domain adapters ops memory overlay (dry-run) ===" -ForegroundColor Cyan
& py scripts/build_mkm_ops_memory_domain_adapters_overlay_v1.py --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== [3/6] route_mkm_ops_memory_pack design/audio topics ===" -ForegroundColor Cyan
& py scripts/route_mkm_ops_memory_pack_v1.py --topic "pixel battalion sprite mkmlife design"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py scripts/route_mkm_ops_memory_pack_v1.py --topic "lens audio bgm musicgen tempo"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipPixelGate) {
    Write-Host "`n=== [4/6] pixel sprite gate (disk SSOT, local files) ===" -ForegroundColor Cyan
    & py scripts/check_mkmlife_pixel_sprite_urls_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipAudioPytest) {
    Write-Host "`n=== [5/6] lens audio offline pytest ===" -ForegroundColor Cyan
    & py -m pytest tests/test_musicgen_numeric_conditioning_v1.py tests/test_check_mkm_ops_sync_bridge_domain_adapters_v1.py tests/test_mkm_ops_memory_domain_adapters_overlay_v1.py -q --tb=short
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "`nOK: domain adapter pointer smoke completed." -ForegroundColor Green
exit 0
