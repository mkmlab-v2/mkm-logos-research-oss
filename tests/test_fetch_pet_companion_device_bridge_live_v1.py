from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
FETCH = ROOT / "scripts/fetch_pet_companion_device_bridge_live_v1.py"
FIXTURE = ROOT / "docs/final/artifacts/fixtures/pet_companion_device_memory_bridge_v1_fixture.json"


def _run_fetch(*extra: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(FETCH), *extra]
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")


def test_build_bridge_request_dry_run_exit_0():
    proc = _run_fetch("--dry-run")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload.get("ok") is True
    assert payload.get("dry_run") is True
    req_path = ROOT / "reports/pet_companion_device_bridge_live_request_latest.json"
    assert req_path.is_file()
    req = json.loads(req_path.read_text(encoding="utf-8"))
    assert req["schema"] == "pet_companion_device_memory_bridge_request_v1"
    assert req["research_only"] is True


def test_validate_response_rejects_schema_mismatch():
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("fetch_bridge", FETCH)
    assert spec and spec.loader
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    errs = mod.validate_response({"schema": "wrong"}, request_id="req-12345678")
    assert "schema_mismatch" in errs


def test_post_bridge_mocked_success(tmp_path: Path):
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("fetch_bridge2", FETCH)
    assert spec and spec.loader
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)

    req = mod.build_request_from_artifacts(
        fixture_path=FIXTURE,
        slots_path=ROOT / "reports/pet_companion_memory_slots_latest.json",
        profile_id="pet-demo-001",
        scenario="health_check",
        question_masked="test question masked",
    )
    mock_resp = json.loads(FIXTURE.read_text(encoding="utf-8"))["mock_response"]
    mock_resp = dict(mock_resp)
    mock_resp["request_id"] = req["request_id"]

    with patch.object(mod, "post_bridge", return_value=(200, mock_resp)):
        status, body = mod.post_bridge("https://mkmlife.com", req, timeout_s=5.0)
    assert status == 200
    assert mod.validate_response(body, request_id=req["request_id"]) == []
