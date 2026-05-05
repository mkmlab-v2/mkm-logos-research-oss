from __future__ import annotations

import json
from pathlib import Path

from scripts import prioritize_sasang_gt_expansion_queue as mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_prioritize_selects_top_k(tmp_path: Path, monkeypatch) -> None:
    queue = tmp_path / "queue.jsonl"
    out = tmp_path / "top.jsonl"
    report = tmp_path / "report.json"
    _write_jsonl(
        queue,
        [
            {"sample_id": "A", "suggested_parent": "SY", "suggested_confidence": 0.9, "source_file": "sasang_predictions_from_btrack_eval_full_mapped_latest.jsonl"},
            {"sample_id": "B", "suggested_parent": "SE", "suggested_confidence": 0.6, "source_file": "sasang_predictions_from_btrack_candidate_subset_latest.jsonl"},
        ],
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "prioritize_sasang_gt_expansion_queue.py",
            "--queue",
            str(queue),
            "--out",
            str(out),
            "--report",
            str(report),
            "--top-k",
            "1",
        ],
    )
    assert mod.main() == 0
    rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 1
    assert rows[0]["sample_id"] == "A"
