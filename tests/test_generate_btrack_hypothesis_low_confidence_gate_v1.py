"""Integration: frozen hypothesis applies min_direction_confidence gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_generate_hypothesis_applies_low_confidence_gate() -> None:
    script = _ROOT / "scripts" / "generate_btrack_hypothesis_prophecy_v1.py"
    out = _ROOT / "docs" / "final" / "artifacts" / "btrack_hypothesis_prophecy_latest.json"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    pred = doc.get("prediction") or {}
    meta = doc.get("runtime_meta") or {}
    gate = meta.get("low_confidence_direction_gate") or {}
    conf = float(pred.get("confidence") or 0)
    thresh = float(gate.get("threshold") or 0.25)
    if conf < thresh and gate.get("prior_direction") in ("bull", "bear"):
        assert pred.get("direction") == "neutral"
        assert gate.get("applied") is True
    elif conf < thresh:
        assert pred.get("direction") == "neutral"
