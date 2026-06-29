"""KRV versification sidecar + bskorea book code smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bskorea_joel_book_code_fetches():
    from scripts.fetch_logos_krv_corpus_from_bskorea_v1 import LOGOS_TO_BSK, _fetch_chapter

    assert LOGOS_TO_BSK["Joel"] == "jol"
    assert len(_fetch_chapter("jol", 1)) >= 10


def test_versification_sidecar_build():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_krv_versification_sidecar_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1), proc.stdout + proc.stderr
    art = ROOT / "docs/final/artifacts/logos_krv_versification_sidecar_v1_latest.json"
    doc = json.loads(art.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_krv_versification_sidecar_v1"
    assert doc["send_gate"] == "HOLD"


def test_governance_hold_gate():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_logos_bible_full_governance_hold_gate_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
