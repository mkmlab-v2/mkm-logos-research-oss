from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_dss_4d_projection_report_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "report_dss_4d_projection.py"
    out = root / "reports" / "constitution" / "btrack_pilot" / "dss_4d_projection_latest.json"
    r = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_dss_4d_projection_v1"
    assert isinstance(doc.get("fact"), dict)
    assert isinstance(doc.get("hypo"), dict)
    fact = doc["fact"]
    assert int(fact.get("input_row_count", 0)) > 0
    assert 0.0 <= float(fact.get("state16_coverage_rate", -1.0)) <= 1.0
