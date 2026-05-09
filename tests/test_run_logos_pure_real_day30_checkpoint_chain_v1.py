from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_pure_real_day30_checkpoint_chain_v1.py"


def test_run_day30_checkpoint_chain_smoke(tmp_path: Path):
    out_json = tmp_path / "checkpoint.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target-unique-days",
            "10",
            "--max-allowed-delta",
            "0.2",
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    # Either pass (0) or fail-close (2) is acceptable for smoke.
    assert cp.returncode in (0, 2), cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_pure_real_day30_checkpoint_chain_v1"
    assert "checkpoint" in doc
    assert "steps" in doc

