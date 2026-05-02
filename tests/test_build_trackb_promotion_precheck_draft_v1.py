# @MKM12-METADATA
# Type: Logic
# Purpose: Track B promotion precheck draft builder regression
# Keywords: trackb, promotion, precheck

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "build_trackb_promotion_precheck_draft_v1.py"


def test_builder_emits_schema(tmp_path: Path) -> None:
    out = tmp_path / "precheck.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--output",
            str(out),
            "--weekly-refresh-ms",
            "100",
            "--runtime-budget-ms",
            "300000",
            "--weekly-exit-code",
            "0",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "trackb_promotion_precheck_draft_v1"
    assert doc.get("checks", {}).get("runtime_budget_ok") is True
    assert doc.get("decision") == "HOLD_PROMOTION_PRECHECK_DRAFT"


def test_builder_missing_inputs_exits_2(tmp_path: Path) -> None:
    out = tmp_path / "bad.json"
    fake = tmp_path / "nope.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--output",
            str(out),
            "--robust",
            str(fake),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert cp.returncode == 2
