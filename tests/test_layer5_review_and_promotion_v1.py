from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE_SCRIPT = ROOT / "scripts" / "build_layer5_review_queue_v1.py"
PROMOTE_SCRIPT = ROOT / "scripts" / "promote_layer5_approved_goldset_v1.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_review_queue_and_promotion(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    queue = tmp_path / "queue.jsonl"
    queue_sum = tmp_path / "queue_summary.json"
    gold = tmp_path / "gold.jsonl"
    gold_sum = tmp_path / "gold_summary.json"

    _write_jsonl(
        candidates,
        [
            {"case_id": "c1", "review_status": "draft", "expected_block": True, "expected_reasons": ["hold", "alert"]},
            {"case_id": "c2", "review_status": "draft", "expected_block": False, "expected_reasons": []},
            {"case_id": "c3", "review_status": "approved", "expected_block": True, "expected_reasons": ["block"]},
        ],
    )

    proc_q = subprocess.run(
        [
            "py",
            str(QUEUE_SCRIPT),
            "--input-jsonl",
            str(candidates),
            "--output-jsonl",
            str(queue),
            "--summary-json",
            str(queue_sum),
            "--max-items",
            "10",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_q.returncode == 0, proc_q.stdout + proc_q.stderr
    queue_rows = [json.loads(x) for x in queue.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(queue_rows) == 2
    assert queue_rows[0]["case_id"] == "c1"

    proc_p = subprocess.run(
        [
            "py",
            str(PROMOTE_SCRIPT),
            "--input-jsonl",
            str(candidates),
            "--output-jsonl",
            str(gold),
            "--summary-json",
            str(gold_sum),
            "--sample-size",
            "10",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_p.returncode == 0, proc_p.stdout + proc_p.stderr
    gold_rows = [json.loads(x) for x in gold.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(gold_rows) == 1
    assert gold_rows[0]["case_id"] == "c3"
