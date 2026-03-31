from __future__ import annotations

import json
from pathlib import Path

from scripts import evaluate_sasang_clinical_metrics as mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_sasang_clinical_eval_generates_expected_metrics(tmp_path: Path, monkeypatch) -> None:
    cohort = tmp_path / "cohort.jsonl"
    preds = tmp_path / "preds.jsonl"
    out = tmp_path / "report.json"

    _write_jsonl(
        cohort,
        [
            {"sample_id": "s1", "text": "t1", "expected_parent": "TY"},
            {"sample_id": "s2", "text": "t2", "expected_parent": "SY"},
            {"sample_id": "s3", "text": "t3", "expected_parent": "TE"},
            {"sample_id": "s4", "text": "t4", "expected_parent": "SE"},
        ],
    )
    _write_jsonl(
        preds,
        [
            {"sample_id": "s1", "predicted_parent": "TY", "confidence": 0.90},
            {"sample_id": "s2", "predicted_parent": "TY", "confidence": 0.70},
            {"sample_id": "s3", "predicted_parent": "TE", "confidence": 0.80},
            {"sample_id": "s4", "predicted_parent": "SE", "confidence": 0.95},
        ],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "evaluate_sasang_clinical_metrics.py",
            "--cohort",
            str(cohort),
            "--predictions",
            str(preds),
            "--out",
            str(out),
            "--ece-bins",
            "5",
        ],
    )

    assert mod.main() == 0
    report = json.loads(out.read_text(encoding="utf-8"))

    assert report["schema"] == "sasang_clinical_eval_v1"
    assert report["diagnostics"]["paired_rows"] == 4
    assert abs(report["metrics"]["accuracy"] - 0.75) < 1e-9
    assert report["metrics"]["confidence"]["available"] is True
    assert report["metrics"]["confidence"]["count"] == 4
    assert len(report["metrics"]["confidence"]["bins"]) == 5

