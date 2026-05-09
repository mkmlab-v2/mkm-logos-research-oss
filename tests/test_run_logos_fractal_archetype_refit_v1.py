from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_fractal_archetype_refit_v1.py"
MATRIX = ROOT / "docs" / "final" / "artifacts" / "logos_fractal_archetype_4d_matrix_v1.json"


def test_run_logos_fractal_archetype_refit_smoke(tmp_path: Path):
    out_json = tmp_path / "refit.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--matrix-json",
            str(MATRIX),
            "--output-json",
            str(out_json),
            "--iterations",
            "20",
            "--seed",
            "7",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_fractal_archetype_refit_v1"
    assert doc.get("source_track") == "B"
    assert doc.get("research_only") is True
    assert int((doc.get("search_meta") or {}).get("iterations", 0)) == 20
    assert "baseline" in doc
    assert "best" in doc
    assert len((doc.get("best") or {}).get("archetypes") or []) >= 1

