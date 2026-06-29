# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_krx_jsonl_builds_30_rows(tmp_path: Path) -> None:
    out = tmp_path / "swarm.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "build_swarm_sentiment_synthetic_krx_jsonl_v1.py"),
            "--date-from",
            "2026-04-01",
            "--date-to",
            "2026-06-12",
            "--calendar-mode",
            "krx_weekdays",
            "--out-jsonl",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 30
    row = json.loads(lines[0])
    assert row["simulation_meta"]["engine_name"] == "synthetic_date_hash_v1"
