from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_fractal_sign_reading_v1.py"
NEWS_FIX = ROOT / "tests" / "fixtures" / "logos_symbolic_event_backtest_news_smoke_v1.jsonl"
MATRIX = ROOT / "docs" / "final" / "artifacts" / "logos_fractal_archetype_4d_matrix_v1.json"


def test_run_logos_fractal_sign_reading_smoke(tmp_path: Path):
    out_json = tmp_path / "fractal.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--news-jsonl",
            str(NEWS_FIX),
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
    assert doc.get("schema") == "logos_fractal_sign_reading_v1"
    assert doc.get("source_track") == "B"
    assert doc.get("research_only") is True
    assert doc.get("inputs", {}).get("news_row_count") == 4
    vec = doc.get("current_vector_slkm") or {}
    for k in ("S", "L", "K", "M"):
        assert k in vec
        assert 0.0 <= float(vec[k]) <= 1.0
    top = doc.get("top_match") or {}
    assert "archetype_id" in top
    assert "resonance_cosine" in top

