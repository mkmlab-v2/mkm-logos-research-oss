#!/usr/bin/env python3
"""Tests for logos gold router canonical materialize."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/materialize_logos_gold_router_canonical_v1.py"
ROUTER = ROOT / "reports/magic_orb_insight_by_query/router_q02_latest.json"


def test_materialize_canonicalizes_verse_ref_aliases(tmp_path: Path) -> None:
    if not ROUTER.is_file():
        return
    backup = tmp_path / "router_q02_backup.json"
    backup.write_text(ROUTER.read_text(encoding="utf-8"), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--query-id", "q02"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(ROUTER.read_text(encoding="utf-8"))
    assert body["verse_ids"][0] == "Jer.1.10"
    assert all(not str(v).startswith("verse_ref:") for v in body["verse_ids"])
    ROUTER.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
