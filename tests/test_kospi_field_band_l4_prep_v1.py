"""L4 prep packet after L3 ack."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


@pytest.mark.skipif(
    not (ROOT / "docs/final/artifacts/kospi_field_band_commander_ack_v1_latest.json").is_file(),
    reason="L3 ack missing",
)
def test_l4_prep_packet_after_l3():
    cp = subprocess.run(
        [PY, "scripts/build_kospi_field_band_l4_prep_packet_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (ROOT / "docs/final/artifacts/kospi_field_band_l4_prep_packet_v1_latest.json").read_text(encoding="utf-8-sig")
    )
    assert doc["promotion_ready"] is False
    assert doc["track_a_go"] is False
    assert doc["track_a_discussion_eligible"] == doc["small_sample_guardrails"]["track_a_discussion_eligible"]
    assert int(doc["summary_metrics"].get("extended_prophecy_n_scored") or 0) >= 100
    assert "small_sample_guardrails" in doc
    assert doc["small_sample_guardrails"]["mixed_panel_headline_kpi_forbidden"] is True
    assert doc["l3_ack_reference"] == "COMMANDER-KOSPI-BAND-L3-ACK-2026-06-23"
