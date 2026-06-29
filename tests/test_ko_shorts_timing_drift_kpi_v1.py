"""Offline tests for ko_shorts timing drift KPI builder."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_ko_shorts_timing_drift_kpi_v1 import _drift_row_from_spike, build_drift_kpi_v1


def test_drift_row_from_spike(tmp_path: Path):
    spike = tmp_path / "ko_shorts_stt_timing_web_deeply_v1_latest.json"
    spike.write_text(
        json.dumps(
            {
                "aligned_word_count": 10,
                "p1_segment_count": 3,
                "drift_vs_proportional": {"start_drift_ms_mean": 100.0, "pairs": 2},
            }
        ),
        encoding="utf-8",
    )
    row = _drift_row_from_spike(spike, json.loads(spike.read_text(encoding="utf-8")))
    assert row["case_id"] == "web_deeply"
    assert row["start_drift_ms_mean"] == 100.0


def test_build_drift_kpi_smoke():
    doc = build_drift_kpi_v1()
    assert doc["schema"] == "ko_shorts_timing_drift_kpi_v1"
    assert doc["send_gate"] == "HOLD"
    assert isinstance(doc.get("spike_drift_rows"), list)
