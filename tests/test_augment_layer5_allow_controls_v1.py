from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "augment_layer5_allow_controls_v1.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_augment_adds_allow_controls(tmp_path: Path) -> None:
    queue = tmp_path / "queue.jsonl"
    source = tmp_path / "source.jsonl"
    summary = tmp_path / "sum.json"
    _write_jsonl(queue, [{"case_id": "x1", "review_status": "draft", "expected_block": True}])
    _write_jsonl(
        source,
        [
            {"high_reliability_gate": "pass", "promotion_gate": "pass"},
            {"high_reliability_gate": "hold"},
        ],
    )
    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--queue-jsonl",
            str(queue),
            "--source-jsonl",
            str(source),
            "--summary-json",
            str(summary),
            "--target-allow-draft",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rows = [json.loads(x) for x in queue.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert any((r.get("expected_block") is False and r.get("review_status") == "draft") for r in rows)
