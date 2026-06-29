from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_external_validation_d6_aux_readiness_v1 as readiness_mod
import run_external_validation_d6_aux_runner_v1 as runner_mod


def test_gate_snapshot_uses_manifest_baseline_when_hybrid_missing(tmp_path):
    gate = runner_mod._gate_snapshot(
        tmp_path,
        {
            "send_gate": "HOLD",
            "ready_for_external_send": False,
            "readiness_all_ok": False,
        },
    )
    assert gate["gate_source"] == "manifest_baseline"
    assert gate["send_gate"] == "HOLD"


def test_check_external_validation_d6_aux_readiness_v1_reports_missing_scripts(tmp_path):
    share = tmp_path / "share"
    share.mkdir()
    ws = tmp_path / "ws"
    ws.mkdir()
    manifest = {
        "reproduce_week1": [
            "powershell -File scripts\\Invoke-MkmHighDelegationPreflight_v1.ps1",
            "py scripts/run_compression_proof_completion_chain_v1.py",
            "python -m pytest tests/test_edge_encoder_sdk_v1.py -q",
        ],
        "artifact_checks": ["reports/mkm_high_delegation_preflight_v1_latest.json"],
    }
    (share / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    (share / "d6_job_request_v1.json").write_text(
        json.dumps({"main_git_head": "abc123"}) + "\n",
        encoding="utf-8",
    )

    doc = readiness_mod.check(
        workspace_root=ws,
        share_dir=share,
        manifest_path=share / "manifest.json",
        expected_git_head="abc123",
    )
    assert doc["status"] == "fail"
    assert doc["summary"]["scripts_ok"] is False
    assert doc["summary"]["tests_ok"] is False
