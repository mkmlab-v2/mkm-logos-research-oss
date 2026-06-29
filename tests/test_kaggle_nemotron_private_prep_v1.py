"""Private Nemotron Kaggle prep smoke (no network, no MKM)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREP = ROOT / "scripts" / "run_kaggle_nemotron_private_prep_v1.py"
TRAIN_CSV = ROOT / "data/kaggle/nvidia-nemotron-model-reasoning-challenge/train.csv"


def test_train_csv_exists() -> None:
    assert TRAIN_CSV.is_file(), "run download script first"


def test_prep_limit_4(tmp_path: Path) -> None:
    out_report = tmp_path / "prep.json"
    out_jsonl = tmp_path / "sft.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(PREP),
            "--limit",
            "4",
            "--out-report-json",
            str(out_report),
            "--out-train-jsonl",
            str(out_jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    body = json.loads(out_report.read_text(encoding="utf-8"))
    assert body["schema"] == "kaggle_nemotron_private_prep_v1"
    assert body["mkm_core_exposed"] is False
    assert body["outputs"]["sft_rows_written"] == 4
    lines = out_jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 4
