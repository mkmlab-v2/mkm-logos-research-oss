from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "run_truthfulqa_ab_benchmark_v1.py"


def test_truthfulqa_benchmark_generate_sample_dataset(tmp_path: Path) -> None:
    dataset = tmp_path / "truthfulqa_sample.jsonl"
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--generate-sample-dataset",
            "--dataset-jsonl",
            str(dataset),
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 0, cp.stderr
    assert dataset.is_file()
    rows = [json.loads(x) for x in dataset.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) >= 2
    assert "question" in rows[0]
    assert "choices" in rows[0]
    assert "correct_choice_index" in rows[0]


def test_truthfulqa_benchmark_script_exists() -> None:
    assert _SCRIPT.is_file(), str(_SCRIPT)


def test_truthfulqa_generation_benchmark_generate_sample_dataset(tmp_path: Path) -> None:
    dataset = tmp_path / "truthfulqa_generation_sample.jsonl"
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--task",
            "generation",
            "--generate-sample-dataset",
            "--dataset-jsonl",
            str(dataset),
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 0, cp.stderr
    assert dataset.is_file()
    rows = [json.loads(x) for x in dataset.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) >= 2
    assert "question" in rows[0]
    assert "correct_answers" in rows[0]
    assert "incorrect_answers" in rows[0]
