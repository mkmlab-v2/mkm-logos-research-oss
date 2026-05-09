from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_temporal_holdout_pack_v1.py"
BUILD_BALANCED = ROOT / "scripts" / "build_logos_non_synthetic_date_balanced_news_v1.py"


def test_run_logos_temporal_holdout_pack_smoke(tmp_path: Path):
    cp_build = subprocess.run(
        [
            sys.executable,
            str(BUILD_BALANCED),
            "--max-per-day",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_build.returncode == 0, cp_build.stderr + cp_build.stdout

    out_json = tmp_path / "temporal_pack.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--bins",
            "3",
            "--min-non-synth-per-bin",
            "2",
            "--group-by-date",
            "--use-non-synthetic-date-balanced",
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_temporal_holdout_pack_v1"
    assert doc.get("source_track") == "B"
    assert doc.get("research_only") is True
    assert int(doc.get("bins_built", 0)) >= 1
    assert int(doc.get("min_non_synth_per_bin_requested", 0)) == 2
    assert doc.get("group_by_date") is True
    assert doc.get("use_non_synthetic_date_balanced") is True
    assert "summary" in doc

