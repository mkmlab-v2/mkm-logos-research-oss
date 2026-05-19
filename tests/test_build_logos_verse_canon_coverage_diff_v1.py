# @MKM12-METADATA
# Type: Logic
# Purpose: Logos verse canon coverage diff v1 regression.
# Keywords: logos, canon, coverage, track_b

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "build_logos_verse_canon_coverage_diff_v1.py"
_FIXTURE_FULL = _ROOT / "tests" / "fixtures" / "logos_verse_canon_coverage_diff_full_min.json"
_FIXTURE_V2 = _ROOT / "tests" / "fixtures" / "logos_verse_canon_coverage_diff_v2_min.jsonl"


def test_runner_exists() -> None:
    assert _RUNNER.is_file()


def test_diff_minimal_fixture(tmp_path: Path) -> None:
    out = tmp_path / "diff.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--full",
            str(_FIXTURE_FULL),
            "--v2",
            str(_FIXTURE_V2),
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_verse_canon_coverage_diff_v1"
    assert doc["counts"]["full_canon_verse_count"] == 3
    assert doc["counts"]["verse_decoded_v2_count"] == 1
    assert doc["counts"]["gap_count"] == 2
    assert set(doc["missing_verse_ids"]) == {"Gen.1.2", "Mark.1.1"}
    assert doc["interpretation"]["phase1_logos_verse_4d_rows_dropped"] == 0
