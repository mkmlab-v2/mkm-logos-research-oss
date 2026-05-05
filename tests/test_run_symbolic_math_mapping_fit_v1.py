from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_symbolic_math_mapping_fit_v1.py"
PAIRS = ROOT / "tests" / "fixtures" / "symbolic_mapping_demo_pairs_v1.jsonl"


def test_run_symbolic_math_mapping_fit_v1(tmp_path: Path) -> None:
    out = tmp_path / "symbolic_fit.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--pairs-jsonl",
            str(PAIRS),
            "--w-dist-grid",
            "0.6,0.7",
            "--w-consistency-grid",
            "0.3,0.4",
            "--top-k",
            "2",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "symbolic_math_mapping_fit_v1"
    assert doc["inputs"]["pair_count"] == 4
    assert len(doc["top_candidates"]) == 2
    assert "w_dist" in doc["summary"]["best_weights"]
