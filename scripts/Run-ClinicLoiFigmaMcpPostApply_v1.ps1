# Post-apply automation after Figma MCP use_figma (local gate; no human paste).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

& py scripts/build_clinic_loi_figma_mcp_apply_handoff_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py scripts/build_clinic_loi_tokens_studio_import_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-ClinicLoiFigmaReverseSyncAuto_v1.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: clinic LOI Figma MCP post-apply chain (record result via record_clinic_loi_figma_mcp_apply_result_v1.py)" -ForegroundColor Green
exit 0
