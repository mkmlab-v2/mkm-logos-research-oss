# Logos GTM counsel handoff — bundle + manifest + email draft (human sends mail).
# SEND_GATE: HOLD — does not open external SEND.
param([switch]$SkipBundleRebuild)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

if (-not $SkipBundleRebuild) {
    Write-Host "== counsel_handoff_bundle" -ForegroundColor Cyan
    & py scripts/build_logos_gtm_counsel_handoff_bundle_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "== counsel_export_manifest" -ForegroundColor Cyan
& py scripts/build_logos_gtm_counsel_export_manifest_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== counsel_submission_email_draft" -ForegroundColor Cyan
& py scripts/emit_logos_gtm_counsel_submission_email_draft_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "OK: Logos counsel handoff chain (human: send email from draft)" -ForegroundColor Green
Write-Host "draft: docs/final/artifacts/logos_gtm_counsel_submission_email_draft_v1_latest.json"
Write-Host "manifest: docs/final/artifacts/logos_gtm_counsel_export_manifest_v1_latest.json"
exit 0
