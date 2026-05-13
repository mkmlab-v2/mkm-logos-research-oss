from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_myeongri_deterministic_lora_inference_eval_v1.py"
FIXTURE = ROOT / "tests" / "fixtures" / "myeongri_deterministic_lora_golden_sample_v1.jsonl"


def test_oracle_golden_alignment_on_fixture(tmp_path: Path) -> None:
    report = tmp_path / "eval_report.json"
    preds = tmp_path / "preds.jsonl"
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--golden-jsonl",
        str(FIXTURE),
        "--oracle-golden",
        "--predictions-jsonl",
        str(preds),
        "--report-json",
        str(report),
    ]
    subprocess.check_call(cmd, cwd=str(ROOT))
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc.get("rows") == 2
    assert doc.get("parse_ok") == 2
    assert doc.get("exact_match_normalized") == 2
    assert doc.get("alignment_pass_rate") == 1.0
