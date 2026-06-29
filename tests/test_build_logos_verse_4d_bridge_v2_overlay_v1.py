# -*- coding: utf-8 -*-
"""Smoke: bridge_v2 overlay builder (reports-only, B-track)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_logos_verse_4d_bridge_v2_overlay_v1.py"
INPUT = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"


def test_bridge_v2_overlay_smoke_max_rows() -> None:
    if not INPUT.is_file():
        return
    out_jsonl = ROOT / "reports/tmp_logos_bridge_v2_overlay_smoke.jsonl"
    out_manifest = ROOT / "reports/tmp_logos_bridge_v2_overlay_smoke.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--input-jsonl",
            str(INPUT),
            "--out-jsonl",
            str(out_jsonl),
            "--out-manifest",
            str(out_manifest),
            "--max-rows",
            "50",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    keys: set[tuple[float, float, float, float]] = set()
    with out_jsonl.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            assert row.get("bridge_v2_hypo", {}).get("research_only") is True
            v = row["vector_4d"]
            keys.add(tuple(round(v[k], 4) for k in ("S", "L", "K", "M")))
    assert len(keys) >= 40
