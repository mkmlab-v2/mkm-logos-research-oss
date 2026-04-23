from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_validate_canon_singularity_weekly_brief_v1(tmp_path: Path):
    src = tmp_path / "weekly.json"
    out = tmp_path / "gate.json"
    src.write_text(
        json.dumps(
            {
                "schema": "original_corpus_regime_singularity_canon_weekly_brief_v1",
                "counts": {"insight_events_in_window": 2, "gate_events_in_window": 2, "gate_fail_count": 0},
                "highlights": {"health_level": "green"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        "scripts/core/validate_canon_singularity_weekly_brief_v1.py",
        "--input-json",
        str(src),
        "--max-gate-fail",
        "0",
        "--output-json",
        str(out),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["status"] == "pass"

