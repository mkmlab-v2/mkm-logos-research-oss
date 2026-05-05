from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIT = ROOT / "scripts" / "run_symbolic_math_mapping_fit_v1.py"
GATE = ROOT / "scripts" / "run_symbolic_math_mapping_shadow_gate_v1.py"
PAIRS = ROOT / "tests" / "fixtures" / "symbolic_mapping_demo_pairs_v1.jsonl"
STREAM = ROOT / "tests" / "fixtures" / "symbolic_mapping_shadow_stream_v1.jsonl"


def test_run_symbolic_math_mapping_shadow_gate_v1(tmp_path: Path) -> None:
    fit_out = tmp_path / "fit.json"
    r_fit = subprocess.run(
        [
            sys.executable,
            str(FIT),
            "--pairs-jsonl",
            str(PAIRS),
            "--out",
            str(fit_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r_fit.returncode == 0, r_fit.stderr

    gate_out = tmp_path / "gate.json"
    r_gate = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--fit-json",
            str(fit_out),
            "--stream-jsonl",
            str(STREAM),
            "--out",
            str(gate_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r_gate.returncode == 0, r_gate.stderr
    doc = json.loads(gate_out.read_text(encoding="utf-8"))
    assert doc["schema"] == "symbolic_math_mapping_shadow_gate_v1"
    assert doc["decision"] in {"PASS_SHADOW_STABLE", "HOLD_SHADOW_UNSTABLE"}
    assert doc["metrics"]["sample_count"] >= 1
