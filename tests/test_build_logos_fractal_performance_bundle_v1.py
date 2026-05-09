from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_fractal_performance_bundle_v1.py"


def test_build_logos_fractal_performance_bundle_smoke(tmp_path: Path):
    out_json = tmp_path / "bundle.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_fractal_performance_bundle_v1"
    assert doc.get("source_track") == "B"
    assert doc.get("research_only") is True
    assert doc.get("summary", {}).get("run_count", 0) >= 1

