from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts import export_sasang_gt_labeling_sheet as mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_export_labeling_sheet_creates_expected_columns(tmp_path: Path, monkeypatch) -> None:
    queue = tmp_path / "priority.jsonl"
    csv_out = tmp_path / "labeling.csv"
    report_out = tmp_path / "report.json"
    _write_jsonl(
        queue,
        [
            {
                "sample_id": "S1",
                "suggested_parent": "SY",
                "suggested_confidence": 0.8,
                "source_file": "predictions.real.latest.jsonl",
                "priority_score": 0.82,
            }
        ],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "export_sasang_gt_labeling_sheet.py",
            "--queue",
            str(queue),
            "--csv-out",
            str(csv_out),
            "--report-out",
            str(report_out),
        ],
    )
    assert mod.main() == 0

    with csv_out.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["sample_id"] == "S1"
    assert rows[0]["label_status"] == "PENDING_HUMAN_LABEL"
