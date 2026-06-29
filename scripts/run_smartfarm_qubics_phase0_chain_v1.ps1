# Phase 0 QuBICS chain: pytest + dry-run E2E check
$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

Write-Host "[1/3] smartfarm pytest ..."
py -m pytest tests/test_ai_smartfarm_qubics_ingest_v1.py tests/test_normalize_qubics_coconet_v1.py tests/test_smartfarm_qubics_mqtt_control_v1.py tests/test_smartfarm_qubics_mqtt_uplink_v1.py tests/test_smartfarm_persist_jsonl_v1.py tests/test_smartfarm_vendor_poll_adapter_v1.py -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] mqtt uplink dry-run ..."
py scripts/check_smartfarm_qubics_mqtt_uplink_dry_run_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/3] phase0 e2e dry-run ..."
py scripts/check_smartfarm_qubics_phase0_e2e_v1.py
exit $LASTEXITCODE
