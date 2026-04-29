from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts import validate_sasang_gt_labeling_sheet as mod


def test_validate_labeling_sheet_detects_invalid_approved_parent(tmp_path: Path, monkeypatch) -> None:
    sheet = tmp_path / "sheet.csv"
    out = tmp_path / "validation.json"

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
        writer.writerow(
            {
                "sample_id": "S1",
                "suggested_parent": "SY",
                "suggested_confidence": "0.8",
                "source_file": "predictions.real.latest.jsonl",
                "priority_score": "0.81",
                "approved_parent": "",
                "label_status": "APPROVED_HUMAN_LABEL",
                "reviewer_note": "",
            }
        )

    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_sasang_gt_labeling_sheet.py",
            "--sheet-csv",
            str(sheet),
            "--out",
            str(out),
        ],
    )
    assert mod.main() == 1
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["valid_for_import"] is False
    assert doc["invalid_rows_count"] == 1
