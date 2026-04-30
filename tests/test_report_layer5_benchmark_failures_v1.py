from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "report_layer5_benchmark_failures_v1.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_failure_report_extracts_fn(tmp_path: Path) -> None:
    gold = tmp_path / "gold.jsonl"
    bench = tmp_path / "bench.json"
    out = tmp_path / "report.json"
    _write_jsonl(
        gold,
        [
            {"case_id": "c1", "expected_reasons": ["hold", "alert"]},
            {"case_id": "c2", "expected_reasons": []},
        ],
    )
    bench.write_text(
        json.dumps(
            {
                "benchmark_status": "HOLD",
                "metrics": {"recall_block": 0.5},
                "sample_preview": [
                    {"case_id": "c1", "predicted_block": False, "expected_block": True, "reasons": []},
                    {"case_id": "c2", "predicted_block": False, "expected_block": False, "reasons": []},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["py", str(SCRIPT), "--goldset-jsonl", str(gold), "--benchmark-json", str(bench), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "layer5_policy_gate_failure_report_v1"
    assert doc["false_negative_count_in_preview"] == 1
