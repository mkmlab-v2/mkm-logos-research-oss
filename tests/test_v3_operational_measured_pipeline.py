from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "v3_question_logs_mini.jsonl"


def test_v3_pipeline_builds_dataset_and_report(tmp_path: Path) -> None:
    dataset_out = tmp_path / "v3_input_dataset.jsonl"
    sampling_out = tmp_path / "v3_sampling_summary.json"
    performance_out = tmp_path / "v3_performance_report.json"

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_v3_measured_pipeline.py"),
        "--in",
        str(FIXTURE),
        "--dataset-out",
        str(dataset_out),
        "--sampling-summary-out",
        str(sampling_out),
        "--performance-out",
        str(performance_out),
        "--sample-size",
        "8",
        "--seed",
        "7",
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)

    assert dataset_out.is_file()
    assert sampling_out.is_file()
    assert performance_out.is_file()

    rows = [json.loads(line) for line in dataset_out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 8
    assert all("prompt" in r and "response" in r and "split" in r for r in rows)
    assert sorted({r["split"] for r in rows}) == ["test", "train", "val"]

    sampling = json.loads(sampling_out.read_text(encoding="utf-8"))
    assert sampling["schema"] == "v3_sampling_summary_v1"
    assert sampling["sampled_size"] == 8
    assert sampling["split_counts"]["train"] > 0

    perf = json.loads(performance_out.read_text(encoding="utf-8"))
    assert perf["schema"] == "v3_pipeline_performance_report_v1"
    assert perf["dataset_metrics"]["total_records"] == 8
    assert perf["quality_gate"]["pass"] is True
