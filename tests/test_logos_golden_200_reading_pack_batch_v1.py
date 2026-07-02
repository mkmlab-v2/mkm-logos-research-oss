"""Golden-200 reading pack batch + live longtail spot check."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_reading_pack_batch_exit_0():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_golden_200_reading_pack_batch_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    report = json.loads(
        (ROOT / "reports/logos_golden_200_reading_pack_batch_v1_latest.json").read_text(encoding="utf-8")
    )
    assert report.get("ok") is True
    assert report.get("built_count") == 24
    sample = ROOT / "docs/final/artifacts/showroom_logos_isaiah53_suffering_servant_reading_pack_slice_v1_latest.json"
    doc = json.loads(sample.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "showroom_logos_reading_pack_slice_v1"
    assert len(doc["reading_packs"]) == 3
    assert doc["send_gate"] == "HOLD"
