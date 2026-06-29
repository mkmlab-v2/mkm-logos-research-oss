"""Sync PersonaDiary Logos sidebar JSON to no1kmedi public/data."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_sync_personadiary_logos_sidebar_public_v1() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/sync_personadiary_logos_sidebar_public_v1.py")],
        cwd=str(ROOT),
        timeout=30,
    )
    assert proc.returncode == 0
    dst = ROOT / "projects/no1kmedi/public/data/personadiary_logos_sidebar_smoke_v1_latest.json"
    assert dst.is_file()
    doc = json.loads(dst.read_text(encoding="utf-8"))
    assert doc.get("schema") == "personadiary_logos_sidebar_smoke_v1"
    assert doc.get("prophecy_vote") == "none"
    assert len(doc.get("hits") or []) == 3
