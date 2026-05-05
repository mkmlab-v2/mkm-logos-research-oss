from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_layer5_next_review_batch_v1.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_export_next_batch_skips_approved(tmp_path: Path) -> None:
    queue = tmp_path / "queue.jsonl"
    out = tmp_path / "next.csv"
    summary = tmp_path / "sum.json"
    _write_jsonl(
        queue,
        [
            {"case_id": "c1", "review_status": "approved"},
            {"case_id": "c2", "review_status": "draft"},
            {"case_id": "c3", "review_status": "draft"},
        ],
    )
    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--queue-jsonl",
            str(queue),
            "--output-csv",
            str(out),
            "--summary-json",
            str(summary),
            "--batch-size",
            "2",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    csv_text = out.read_text(encoding="utf-8")
    assert "c1" not in csv_text
    assert "c2" in csv_text and "c3" in csv_text
