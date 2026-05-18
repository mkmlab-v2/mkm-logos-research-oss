"""TR full-NT manifest smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_tr_nt_corpus_manifest_v1.py"
FULL_NT = ROOT / "data/logos/manuscripts/tr_greek_by_verse_v1.full_nt.jsonl"
OUT = ROOT / "docs/final/artifacts/logos_tr_nt_corpus_manifest_v1_latest.json"


@pytest.mark.skipif(not FULL_NT.is_file(), reason="full NT TR jsonl not built yet")
def test_tr_nt_manifest_smoke() -> None:
    rc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["row_count"] > 7000
    assert doc["gap_policy_hits"] == 15
