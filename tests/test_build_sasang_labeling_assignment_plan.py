from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts import build_sasang_labeling_assignment_plan as mod


def test_assignment_plan_splits_rows_evenly(tmp_path: Path, monkeypatch) -> None:
    sheet = tmp_path / "sheet.csv"
    plan = tmp_path / "plan.json"
    report = tmp_path / "report.json"

    with sheet.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sample_id",
                "suggested_parent",
                "suggested_confidence",
                "source_file",
                "priority_score",
                "approved_parent",
                "label_status",
                "reviewer_note",
            ],
        )
        writer.writeheader()
        for i in range(6):
            writer.writerow(
                {
                    "sample_id": f"S{i}",
                    "suggested_parent": "SY",
                    "suggested_confidence": "0.8",
                    "source_file": "predictions.real.latest.jsonl",
                    "priority_score": "0.81",
                    "approved_parent": "",
                    "label_status": "PENDING_HUMAN_LABEL",
                    "reviewer_note": "",
                }
            )

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_sasang_labeling_assignment_plan.py",
            "--sheet-csv",
            str(sheet),
            "--plan-out",
            str(plan),
            "--report-out",
            str(report),
            "--reviewers",
            "R1",
            "R2",
        ],
    )
    assert mod.main() == 0
    rep = json.loads(report.read_text(encoding="utf-8"))
    assert rep["rows_per_reviewer"]["R1"] == 3
    assert rep["rows_per_reviewer"]["R2"] == 3
