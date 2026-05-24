"""Contemplation + interpretive bridge local checks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTEMPLATION = ROOT / "scripts" / "run_btrack_prophecy_contemplation_v1.py"


def test_contemplation_interpretive_bridge_guards(tmp_path: Path) -> None:
    b = tmp_path / "bundle.json"
    b.write_text(
        json.dumps(
            {
                "schema": "btrack_llm_input_bundle_v1",
                "version": "1.3.0",
                "artifacts": {
                    "sasang_interpretive_bridge_context": {
                        "available": True,
                        "auto_weight_adjustment_forbidden": True,
                        "track_a_live_routing_forbidden": True,
                        "axis_count": 1,
                        "sections_slice": [{"axis_id": "byeongjeung_yakri", "availability": "partial"}],
                    }
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "contemplation.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(CONTEMPLATION),
            "--bundle",
            str(b),
            "--output",
            str(out),
            "--skip-audit-log",
            "--skip-gemini-reflect",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    ids = [c["id"] for c in doc["review"]["checks"]]
    assert "interpretive_bridge_present" in ids
    assert "interpretive_bridge_safety_flags" in ids
