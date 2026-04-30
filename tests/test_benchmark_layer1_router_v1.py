from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "benchmark_layer1_router_v1.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_layer1_router_benchmark(tmp_path: Path) -> None:
    inp = tmp_path / "goldset.jsonl"
    out = tmp_path / "layer1.json"
    _write_jsonl(
        inp,
        [
            {"case_id": "c1", "user_input": "hold this action", "expected_block": True},
            {"case_id": "c2", "user_input": "normal summary", "expected_block": False},
            {"case_id": "c3", "assistant_output": "policy violation alert", "expected_block": True},
        ],
    )
    proc = subprocess.run(
        ["py", str(SCRIPT), "--input-jsonl", str(inp), "--output-json", str(out), "--min-router-accuracy", "0.9"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "layer1_router_benchmark_v1"
    assert doc["metrics"]["labeled_count"] == 3
    assert doc["benchmark_status"] == "PASS"
