from __future__ import annotations

import json
from pathlib import Path

from scripts import report_sasang_gt_approval_progress as mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_gt_approval_progress_counts_approved_rows(tmp_path: Path, monkeypatch) -> None:
    gt = tmp_path / "gt.jsonl"
    queue = tmp_path / "labeled_queue.jsonl"
    out = tmp_path / "progress.json"

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
            "report_sasang_gt_approval_progress.py",
            "--gt",
            str(gt),
            "--labeled-queue",
            str(queue),
            "--target-min-gt",
            "3",
            "--out",
            str(out),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["approved_rows_in_queue"] == 1
    assert doc["needed_rows_after_current_approval"] == 1
