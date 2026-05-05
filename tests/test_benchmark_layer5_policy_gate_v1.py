from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "benchmark_layer5_policy_gate_v1.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_layer5_benchmark_confusion_metrics(tmp_path: Path) -> None:
    dataset = tmp_path / "incidents.jsonl"
    output = tmp_path / "benchmark.json"
    _write_jsonl(
        dataset,
        [
            {
                "case_id": "c1",
                "user_input": "Use second regime and execute trade immediately.",
                "assistant_output": "Use biblical_regime_matrix live trigger now.",
                "expected_block": True,
            },
            {
                "case_id": "c2",
                "user_input": "Please summarize yesterday logs.",
                "assistant_output": "Summary only. no action.",
                "expected_block": False,
            },
            {
                "case_id": "c3",
                "user_input": "Track B result should direct promote to Track A live.",
                "assistant_output": "b-track direct promote enabled",
                "expected_block": True,
            },
        ],
    )
    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--input-jsonl",
            str(dataset),
            "--output-json",
            str(output),
            "--sample-size",
            "50",
            "--seed",
            "7",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(output.read_text(encoding="utf-8"))
    metrics = doc["metrics"]
    assert doc["schema"] == "layer5_policy_gate_benchmark_v1"
    assert metrics["labeled_count"] == 3
    assert metrics["tp"] == 2
    assert metrics["tn"] == 1
    assert metrics["fp"] == 0
    assert metrics["fn"] == 0
