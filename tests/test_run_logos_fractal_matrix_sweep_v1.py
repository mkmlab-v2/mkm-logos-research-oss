from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_fractal_matrix_sweep_v1.py"
MATRIX = ROOT / "docs" / "final" / "artifacts" / "logos_fractal_archetype_4d_matrix_v1.json"


def test_run_logos_fractal_matrix_sweep_smoke(tmp_path: Path):
    out_json = tmp_path / "sweep.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--matrix-json",
            str(MATRIX),
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_fractal_matrix_sweep_v1"
    assert doc.get("source_track") == "B"
    assert doc.get("research_only") is True
    assert int(doc.get("input_run_count", 0)) >= 1
    cands = doc.get("candidates_top10") or []
    assert len(cands) >= 1
    meta = doc.get("search_meta") or {}
    assert int(meta.get("candidate_count", 0)) >= len(cands)
    assert "best_candidate" in doc

