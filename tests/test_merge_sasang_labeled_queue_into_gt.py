from __future__ import annotations

import json
from pathlib import Path

from scripts import merge_sasang_labeled_queue_into_gt as mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_merge_dry_run_reports_approved_rows(tmp_path: Path, monkeypatch) -> None:
    gt = tmp_path / "gt.jsonl"
    queue = tmp_path / "queue.jsonl"
    out_gt = tmp_path / "out_gt.jsonl"
    report = tmp_path / "report.json"

    _write_jsonl(gt, [{"sample_id": "A", "expected_parent": "SY"}])
    _write_jsonl(
        queue,
        [
            {"sample_id": "B", "approved_parent": "SE", "label_status": "APPROVED_HUMAN_LABEL"},
            {"sample_id": "C", "approved_parent": "TY", "label_status": "PENDING_HUMAN_LABEL"},
        ],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "merge_sasang_labeled_queue_into_gt.py",
            "--gt",
            str(gt),
            "--labeled-queue",
            str(queue),
            "--out-gt",
            str(out_gt),
            "--report",
            str(report),
        ],
    )
    assert mod.main() == 0
    rep = json.loads(report.read_text(encoding="utf-8"))
    assert rep["approved_queue_rows"] == 1
    assert rep["inserted_rows"] == 1
    assert rep["write_mode"] is False
