# @MKM12-METADATA
# Type: Logic
# Purpose: logos gap staging + union merge smoke (Track B).

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STAGING_SCRIPT = ROOT / "scripts/build_logos_verse_gap_staging_v1.py"
MERGE_SCRIPT = ROOT / "scripts/merge_logos_verse_decoded_union_v1.py"
DIFF = ROOT / "reports/constitution/btrack_pilot/logos_verse_canon_coverage_diff_v1_latest.json"


def test_gap_staging_smoke_max_5(tmp_path: Path) -> None:
    if not DIFF.is_file():
        pytest.skip("coverage diff missing")
    out = tmp_path / "staging.jsonl"
    meta = tmp_path / "staging_meta.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(STAGING_SCRIPT),
            "--coverage-diff",
            str(DIFF),
            "--out-jsonl",
            str(out),
            "--out-meta",
            str(meta),
            "--max-rows",
            "5",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 5
    row = json.loads(lines[0])
    assert row.get("gap_staging") is True
    assert row.get("edition") == "MT_SSOT_GAP_STAGING"


def test_union_merge_smoke(tmp_path: Path) -> None:
    v2 = ROOT / "data/logos/verse_decoded_v2.jsonl"
    if not v2.is_file():
        pytest.skip("verse_decoded_v2 missing")
    staging = tmp_path / "staging.jsonl"
    staging.write_text(
        json.dumps(
            {
                "verse_id": "ZZZ.9.9",
                "edition": "MT_SSOT_GAP_STAGING",
                "gap_staging": True,
                "vector_4d": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
                "unified_4d_vector": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "union.jsonl"
    cp = subprocess.run(
        [
            sys.executable,
            str(MERGE_SCRIPT),
            "--v2-jsonl",
            str(v2),
            "--staging-jsonl",
            str(staging),
            "--out-jsonl",
            str(out),
            "--out-meta",
            str(tmp_path / "union_meta.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    ids = {json.loads(ln)["verse_id"] for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()}
    assert "ZZZ.9.9" in ids
