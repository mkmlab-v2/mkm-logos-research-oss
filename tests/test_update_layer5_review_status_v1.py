from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "update_layer5_review_status_v1.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_bulk_status_update_from_csv(tmp_path: Path) -> None:
    src = tmp_path / "queue.jsonl"
    out = tmp_path / "queue_out.jsonl"
    ids = tmp_path / "ids.csv"
    summary = tmp_path / "summary.json"
    _write_jsonl(
        src,
        [
            {"case_id": "c1", "review_status": "draft"},
            {"case_id": "c2", "review_status": "draft"},
            {"case_id": "c3", "review_status": "approved"},
        ],
    )
    ids.write_text("case_id\nc1\nc3\n", encoding="utf-8")

    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--input-jsonl",
            str(src),
            "--output-jsonl",
            str(out),
            "--summary-json",
            str(summary),
            "--ids-file",
            str(ids),
            "--set-status",
            "approved",
            "--only-draft",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    by_id = {r["case_id"]: r for r in rows}
    assert by_id["c1"]["review_status"] == "approved"
    assert by_id["c2"]["review_status"] == "draft"
    assert by_id["c3"]["review_status"] == "approved"
    s = json.loads(summary.read_text(encoding="utf-8"))
    assert s["updated_row_count"] == 1
