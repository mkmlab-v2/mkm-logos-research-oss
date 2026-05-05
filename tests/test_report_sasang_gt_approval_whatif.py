from __future__ import annotations

import json
from pathlib import Path

from scripts import report_sasang_gt_approval_whatif as mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_whatif_reaches_target_with_queue(tmp_path: Path, monkeypatch) -> None:
    gt = tmp_path / "gt.jsonl"
    queue = tmp_path / "queue.jsonl"
    out = tmp_path / "whatif.json"

    _write_jsonl(gt, [{"sample_id": "A", "expected_parent": "SY"}])
    _write_jsonl(queue, [{"sample_id": "B"}, {"sample_id": "C"}])

    monkeypatch.setattr(
        "sys.argv",
        [
            "report_sasang_gt_approval_whatif.py",
            "--gt",
            str(gt),
            "--priority-queue",
            str(queue),
            "--target-min-gt",
            "3",
            "--out",
            str(out),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["can_hit_target_if_full_priority_approved"] is True
