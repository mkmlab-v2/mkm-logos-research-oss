"""Smoke: emit_myeongni_weekly_ops_summary_v1 writes expected sections."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMIT = ROOT / "scripts" / "emit_myeongni_weekly_ops_summary_v1.py"


def test_emit_summary_markdown(tmp_path: Path) -> None:
    lens = tmp_path / "lens.json"
    gate = tmp_path / "gate.json"
    out = tmp_path / "out.md"
    lens.write_text(
        json.dumps({"ts_utc": "2026-01-01T00:00:00Z", "schema": "x", "scores": {"direction_score": 0.1}}),
        encoding="utf-8",
    )
    gate.write_text(
        json.dumps(
            {
                "ts_utc": "2026-01-02T00:00:00Z",
                "decision": "KEEP_OBSERVATION_ONLY",
                "blockers": [],
                "history": {"weekly_cycles_observed": 3, "monthly_cycles_observed": 1},
            }
        ),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(EMIT),
            "--lens-json",
            str(lens),
            "--gate-json",
            str(gate),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    text = out.read_text(encoding="utf-8")
    assert "Shadow gate" in text
    assert "KEEP_OBSERVATION_ONLY" in text
    assert "weekly_cycles_observed: `3`" in text
