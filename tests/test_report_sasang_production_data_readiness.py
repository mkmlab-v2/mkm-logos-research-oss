from __future__ import annotations

import json
from pathlib import Path

from scripts import report_sasang_production_data_readiness as mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_production_data_readiness_detects_low_pairable_rows(tmp_path: Path, monkeypatch) -> None:
    gt = tmp_path / "gt.jsonl"
    pred_dir = tmp_path / "preds"
    out = tmp_path / "readiness.json"

    _write_jsonl(
        gt,
        [
            {"sample_id": "A", "expected_parent": "SY"},
            {"sample_id": "B", "expected_parent": "SE"},
        ],
    )
    _write_jsonl(
        pred_dir / "predictions.real.latest.jsonl",
        [{"sample_id": "A", "predicted_parent": "SY", "confidence": 0.8}],
    )
    _write_jsonl(
        pred_dir / "predictions.synthetic.latest.jsonl",
        [{"sample_id": "B", "predicted_parent": "SE", "confidence": 0.9}],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "report_sasang_production_data_readiness.py",
            "--gt",
            str(gt),
            "--pred-dir",
            str(pred_dir),
            "--out",
            str(out),
        ],
    )

    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ready_for_production_strict"] is False
    assert doc["max_pairable_rows_authoritative"] == 1
