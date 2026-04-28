from __future__ import annotations

import json
from pathlib import Path

from scripts import build_sasang_gt_expansion_queue as mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_gt_expansion_queue_collects_unlabeled_ids(tmp_path: Path, monkeypatch) -> None:
    gt = tmp_path / "gt.jsonl"
    pred_dir = tmp_path / "preds"
    queue_out = tmp_path / "queue.jsonl"
    report_out = tmp_path / "report.json"

    _write_jsonl(gt, [{"sample_id": "A", "expected_parent": "SY"}])
    _write_jsonl(
        pred_dir / "predictions.real.latest.jsonl",
        [
            {"sample_id": "A", "predicted_parent": "SY", "confidence": 0.7},
            {"sample_id": "B", "predicted_parent": "SE", "confidence": 0.9},
        ],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_sasang_gt_expansion_queue.py",
            "--gt",
            str(gt),
            "--pred-dir",
            str(pred_dir),
            "--queue-out",
            str(queue_out),
            "--report-out",
            str(report_out),
            "--target-min-gt",
            "128",
        ],
    )

    assert mod.main() == 0
    rows = [json.loads(x) for x in queue_out.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 1
    assert rows[0]["sample_id"] == "B"
    rep = json.loads(report_out.read_text(encoding="utf-8"))
    assert rep["gt_current_valid_rows"] == 1
    assert rep["gap_rows"] == 127
