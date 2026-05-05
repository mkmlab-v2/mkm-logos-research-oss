from __future__ import annotations

import json
from pathlib import Path

from scripts import export_sasang_labeling_packets_by_reviewer as mod


def test_export_reviewer_packets(tmp_path: Path, monkeypatch) -> None:
    plan = tmp_path / "plan.json"
    out_dir = tmp_path / "packets"
    report = tmp_path / "report.json"
    plan.write_text(
        json.dumps(
            {
                "assignments": {
                    "R1": [{"sample_id": "S1", "suggested_parent": "SY"}],
                    "R2": [{"sample_id": "S2", "suggested_parent": "SE"}],
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "export_sasang_labeling_packets_by_reviewer.py",
            "--plan",
            str(plan),
            "--out-dir",
            str(out_dir),
            "--report-out",
            str(report),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert "R1" in doc["reviewer_packet_files"]
    assert "R2" in doc["reviewer_packet_files"]
