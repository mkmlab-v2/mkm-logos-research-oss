from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts import import_sasang_labeled_sheet_to_queue as mod


def test_import_labeled_sheet_to_queue_counts_approved(tmp_path: Path, monkeypatch) -> None:
    sheet = tmp_path / "sheet.csv"
    out = tmp_path / "labeled.jsonl"
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
        writer.writerow(
            {
                "sample_id": "S1",
                "suggested_parent": "SY",
                "suggested_confidence": "0.9",
                "source_file": "predictions.real.latest.jsonl",
                "priority_score": "0.91",
                "approved_parent": "SY",
                "label_status": "APPROVED_HUMAN_LABEL",
                "reviewer_note": "ok",
            }
        )
        writer.writerow(
            {
                "sample_id": "S2",
                "suggested_parent": "SE",
                "suggested_confidence": "0.8",
                "source_file": "predictions.real.latest.jsonl",
                "priority_score": "0.82",
                "approved_parent": "",
                "label_status": "PENDING_HUMAN_LABEL",
                "reviewer_note": "",
            }
        )

    monkeypatch.setattr(
        "sys.argv",
        [
            "import_sasang_labeled_sheet_to_queue.py",
            "--sheet-csv",
            str(sheet),
            "--out-jsonl",
            str(out),
            "--report-out",
            str(report),
        ],
    )
    assert mod.main() == 0
    rep = json.loads(report.read_text(encoding="utf-8"))
    assert rep["approved_rows"] == 1
