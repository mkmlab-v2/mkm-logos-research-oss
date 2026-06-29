from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_build_lora_pack_latency_extrapolation_v1_runs() -> None:
    out = ROOT / "reports" / "tmp_lora_pack_latency_extrapolation_test.json"
    if out.exists():
        out.unlink()
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_lora_pack_latency_extrapolation_v1.py"),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lora_pack_latency_extrapolation_v1"
    assert doc["efficiency_stats"]["packs_measured"] == 200
    assert doc["efficiency_stats"]["mean_pipeline_elapsed_sec_per_pack"] > 3.0
    grid = {row["packs"]: row for row in doc["canonical_pack_grid"]}
    assert grid[20]["serial_full_refresh_minutes"] > grid[4]["serial_full_refresh_minutes"]
