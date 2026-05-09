from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_logos_fractal_refit_candidate_v1.py"
EVAL_SCRIPT = ROOT / "scripts" / "run_logos_fractal_holdout_eval_v1.py"


def test_run_logos_fractal_holdout_eval_smoke(tmp_path: Path):
    cand_json = tmp_path / "candidate.json"
    cp_build = subprocess.run(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--output-json",
            str(cand_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_build.returncode == 0, cp_build.stderr + cp_build.stdout

    out_json = tmp_path / "holdout_eval.json"
    cp_eval = subprocess.run(
        [
            sys.executable,
            str(EVAL_SCRIPT),
            "--candidate-matrix-json",
            str(cand_json),
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_eval.returncode == 0, cp_eval.stderr + cp_eval.stdout

    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_fractal_holdout_eval_v1"
    assert doc.get("source_track") == "B"
    assert doc.get("research_only") is True
    assert int(doc.get("holdout_tag_count", 0)) >= 1
    assert "baseline_eval" in doc
    assert "candidate_eval" in doc

