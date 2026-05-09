from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_temporal_holdout_compare_backfill_v1.py"


def test_run_logos_temporal_holdout_compare_backfill_smoke(tmp_path: Path):
    out_json = tmp_path / "compare.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--bins",
            "3",
            "--min-non-synth-per-bin",
            "2",
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_temporal_holdout_compare_backfill_v1"
    assert doc.get("source_track") == "B"
    assert "pure_real" in doc
    assert "mixed_backfill" in doc

