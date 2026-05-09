from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_non_synthetic_date_balanced_news_v1.py"
INPUT = ROOT / "docs" / "final" / "artifacts" / "news_observation_v1_latest.jsonl"


def test_build_non_synthetic_date_balanced_news_smoke(tmp_path: Path):
    out_jsonl = tmp_path / "balanced.jsonl"
    out_meta = tmp_path / "balanced_meta.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input-jsonl",
            str(INPUT),
            "--output-jsonl",
            str(out_jsonl),
            "--meta-json",
            str(out_meta),
            "--max-per-day",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    assert out_jsonl.exists()
    meta = json.loads(out_meta.read_text(encoding="utf-8"))
    assert meta.get("schema") == "news_observation_non_synthetic_date_balanced_meta_v1"
    assert int(meta.get("max_per_day", 0)) == 1
    assert int(meta.get("output_row_count", 0)) >= 0

