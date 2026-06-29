# Patient intake internal PoC chain: SEND_GATE confirm → Solapi dry → webhook probe → roundtrip smoke.
param(
    [switch]$SkipConfirm,
    [switch]$SkipWebhookProbe,
    [switch]$SkipRoundtrip
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host "[0/7] sync gate + webhook env bootstrap"
py scripts/sync_patient_intake_gate_snapshot_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/apply_patient_intake_webhook_env_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/sync_patient_intake_gate_snapshot_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$n8nRegister = Join-Path $PSScriptRoot "Register-PatientIntakeN8nWebhook_v1.ps1"
if (Test-Path -LiteralPath $n8nRegister) {
    Write-Host "[0b/7] n8n webhook register (VPS; skip on SSH failure)"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $n8nRegister
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN: n8n register failed (exit $LASTEXITCODE) — probe step may 404 until manual import" -ForegroundColor Yellow
    }
}

Write-Host "[1/7] build solapi dry"
py scripts/build_patient_intake_solapi_dry_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipConfirm) {
    Write-Host "[2/7] confirm internal PoC SEND_GATE"
    py scripts/check_patient_intake_send_gate_v1.py --confirm-internal-poc
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    py scripts/build_patient_intake_solapi_dry_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[2/7] skip confirm"
    py scripts/check_patient_intake_send_gate_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipWebhookProbe) {
    Write-Host "[3/7] probe test webhook (dry if unset)"
    py scripts/probe_patient_intake_notification_webhook_v1.py --non-fatal
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[3/7] skip webhook probe"
}

if (-not $SkipRoundtrip) {
    Write-Host "[4/7] intake roundtrip smoke (production build + next start)"
    $roundtripRunner = Join-Path $Root "projects\no1kmedi\scripts\run-clinic-intake-roundtrip-smoke.ps1"
    if (-not (Test-Path -LiteralPath $roundtripRunner)) {
        throw "Missing roundtrip runner: $roundtripRunner"
    }
    if (-not $env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT = $Root }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $roundtripRunner
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[4/7] skip roundtrip"
}

Write-Host "[5/7] build paste assistant"
py scripts/build_patient_intake_paste_assistant_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/sync_patient_intake_gate_snapshot_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[6/7] gate status"
Write-Host "Invoke-PatientIntakeOpenPoC_v1: ok"
Write-Host "paste: reports/demo/patient_intake_paste_assistant_v1.html"
Write-Host "artifacts: reports/patient_intake_roundtrip_dry_v1_latest.json reports/patient_intake_notification_probe_v1_latest.json"
py scripts/check_patient_intake_send_gate_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
