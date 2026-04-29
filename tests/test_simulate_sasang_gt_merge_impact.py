from __future__ import annotations

import json
from pathlib import Path

from scripts import simulate_sasang_gt_merge_impact as mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_simulation_can_hit_target() -> None:
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as d:
        root = Path(d)
        gt = root / "gt.jsonl"
        queue = root / "q.jsonl"
        out = root / "out.json"
        _write_jsonl(gt, [{"sample_id": "A", "expected_parent": "SY"}])
        _write_jsonl(queue, [{"sample_id": "B"}, {"sample_id": "C"}])

        import sys

        argv = sys.argv
        try:
            sys.argv = [
                "simulate_sasang_gt_merge_impact.py",
                "--gt",
                str(gt),
                "--priority-queue",
                str(queue),
                "--approve-top-n",
                "2",
                "--strict-target-min-gt",
                "3",
                "--out",
                str(out),
            ]
            assert mod.main() == 0
        finally:
            sys.argv = argv

        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["strict_pairable_ready_after_simulation"] is True
