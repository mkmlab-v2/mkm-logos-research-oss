# @MKM12-METADATA
# Type: Logic
# Purpose: Regression for myeongni / sasang / logos independent lens v0 runners.
# Keywords: independent_lens, multilens, b-track

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]

_RUNNERS = (
    ("scripts/run_lens_myeongni.py", "myeongni_independent_lens_v0", "myeongni"),
    ("scripts/run_lens_sasang.py", "sasang_independent_lens_v0", "sasang"),
    ("scripts/run_lens_logos.py", "logos_independent_lens_v0", "logos"),
)


@pytest.mark.parametrize("script_rel,schema,lens_id", _RUNNERS)
def test_runner_emits_schema(tmp_path: Path, script_rel: str, schema: str, lens_id: str) -> None:
    runner = _ROOT / script_rel
    assert runner.is_file(), runner
    out = tmp_path / f"lens_{lens_id}.json"
    cp = subprocess.run(
        [sys.executable, str(runner), "--output", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == schema
    assert doc.get("lens_id") == lens_id
    assert doc.get("hypothesis_tier") == "B"
    assert doc.get("boundary_ack") is True
    scores = doc.get("scores") or {}
    assert -1.0 <= float(scores.get("direction_score", 0)) <= 1.0
    assert 0.0 <= float(scores.get("confidence", 0)) <= 1.0
