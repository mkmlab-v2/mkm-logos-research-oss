from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_generic_llm_judge_shadow_from_eval(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    eval_path = tmp_path / "eval.json"
    eval_path.write_text(
        json.dumps({"weighted_pillars_alignment_pass_rate": 0.76, "parse_ok_rate": 1.0}),
        encoding="utf-8",
    )
    out = tmp_path / "judge.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/build_generic_llm_judge_shadow_v1.py"),
            "--eval-json",
            str(eval_path),
            "--out",
            str(out),
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "generic_llm_judge_shadow_v1"
    assert doc["judge_score"] >= 0.7
