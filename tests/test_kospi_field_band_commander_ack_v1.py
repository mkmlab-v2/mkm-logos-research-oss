"""L3 commander ack packet + record gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_field_band_extended_oos_v1_latest.json").is_file(),
    reason="L2 artifact missing",
)
def test_build_ack_packet_ack_ready():
    from scripts.build_kospi_field_band_commander_ack_packet_v1 import build_commander_ack_packet
    from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read

    l2 = _read(ROOT / "reports/kospi_field_band_extended_oos_v1_latest.json")
    doc = build_commander_ack_packet(
        l2_doc=l2,
        june_wf=_read(ROOT / "reports/kospi_four_lens_conflict_band_coverage_wf_v1_latest.json"),
        shadow=_read(ROOT / "reports/kospi_field_band_shadow_replay_v1_latest.json"),
        tier2_chain=_read(ROOT / "reports/kospi_four_lens_per_lens_tier2_chain_v1_latest.json"),
        nested_revalidate=_read(ROOT / "reports/kospi_field_band_nested_tune_revalidate_v1_latest.json"),
    )
    assert doc["schema"] == "kospi_field_band_commander_ack_packet_v1"
    assert doc["ack_ready"] is True
    assert doc["recommended_commander_action"] == "ACK_L3_BAND_SHADOW_RESEARCH"
    assert len(doc["commander_checklist"]) == 4


def test_record_ack_rejects_without_ready_packet(tmp_path: Path):
    bad_packet = tmp_path / "packet.json"
    bad_packet.write_text(
        json.dumps({"ack_ready": False, "recommended_commander_action": "HOLD_FIX_GATES"}),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            PY,
            "scripts/record_kospi_field_band_commander_ack_v1.py",
            "--ack-reference",
            "TEST-REF",
            "--packet-json",
            str(bad_packet),
            "--skip-local",
            "--out-json",
            str(tmp_path / "out.json"),
            "--log-jsonl",
            str(tmp_path / "log.jsonl"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert cp.returncode == 1


def test_record_ack_with_force(tmp_path: Path):
    from scripts.record_kospi_field_band_commander_ack_v1 import build_ack_doc

    packet = {
        "ack_ready": False,
        "metrics": {},
        "caveats_ko": [],
        "scope_if_ack": {},
        "track_wall": {},
        "evidence_pointers": {},
    }
    doc = build_ack_doc(packet=packet, ack_reference="TEST-FORCE-ACK")
    assert doc["decision"] == "ACK_L3_BAND_SHADOW_RESEARCH"
    assert doc["send_gate"] == "HOLD"
    assert doc["scope_confirmed"]["no_live_trading_inject"] is True


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_field_band_extended_oos_v1_latest.json").is_file(),
    reason="L2 artifact missing",
)
def test_build_packet_cli_exit_zero():
    cp = subprocess.run(
        [PY, "scripts/build_kospi_field_band_commander_ack_packet_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out = json.loads(cp.stdout.strip())
    assert out["ack_ready"] is True
    pkt = json.loads(
        (ROOT / "docs/final/artifacts/kospi_field_band_commander_ack_packet_v1_latest.json").read_text(
            encoding="utf-8-sig"
        )
    )
    assert pkt["ladder_stage"] == "L3_commander_ack_pending"
