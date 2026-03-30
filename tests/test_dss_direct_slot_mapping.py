from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_dss_direct_slot_mapping_report_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "map_dss_rows_to_16_anchor_slots.py"
    out = root / "reports" / "constitution" / "btrack_pilot" / "btrack_dss_direct_slot_mapping_latest.json"
    r = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_dss_direct_slot_mapping_v1"
    inputs = doc.get("inputs", {})
    assert inputs.get("confidence_mode") == "v2"
    kpi = doc.get("kpi", {})
    assert int(kpi.get("slot_count", 0)) == 16
    assert 0.0 <= float(kpi.get("slot_coverage_rate", -1.0)) <= 1.0
    assert 0.0 <= float(kpi.get("traceability_rate", -1.0)) <= 1.0
    assert 0.0 <= float(kpi.get("mean_confidence_boost_base", -1.0)) <= 1.0
    assert 0.0 <= float(kpi.get("mean_confidence_boost", -1.0)) <= 1.0
    assert float(kpi.get("mean_confidence_boost", 0.0)) >= float(kpi.get("mean_confidence_boost_base", 0.0))
