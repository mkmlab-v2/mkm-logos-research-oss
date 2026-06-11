"""Smoke tests for large-scale MKM ops memory bench ([HYPO] / research_only)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bench_mkm_ops_memory_large_scale_v1.py"


def test_large_scale_bench_smoke_exit_zero(tmp_path: Path) -> None:
    out = tmp_path / "large_scale_bench.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--workspace-root",
            str(ROOT),
            "--out",
            str(out),
            "--smoke",
            "--sample-scenarios-in-out",
            "8",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_ops_memory_large_scale_bench_v1"
    assert doc["research_only"] is True
    assert doc["hypothesis_tier"] == "B"
    assert doc["scenario_count"] == 50
    assert "raw" in doc["aggregate"]
    assert "repair_v2" in doc["aggregate"]
    assert "coordinate_v1" in doc["aggregate"]
    assert "delta" in doc["aggregate"]
    assert doc["aggregate"]["delta"]["mean_jaccard_repair_v2_minus_raw"] is not None
    assert doc["gates"]["must_keep_inject_pass_count"] >= 0
    assert doc["sre"]["lookup_ms_p50"] is not None
    assert len(doc["scenario_sample"]) <= 8


def test_generate_scenario_specs_minimum() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from bench_mkm_ops_memory_large_scale_v1 import _generate_scenario_specs

    entries = [{"id": f"e{i}", "path": f"docs/final/x{i}.md", "summary_ko": f"s{i}"} for i in range(5)]
    specs = _generate_scenario_specs(entries, min_scenarios=100, seed=1)
    assert len(specs) == 100
    assert specs[0]["scenario_id"].startswith("ls_")
