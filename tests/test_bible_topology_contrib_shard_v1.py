"""Bible topology contributor shard validate smoke (Repo #2 Phase 1 prep)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
PASSION_SEED = ROOT / "tests/fixtures/bible_topology/sample/sample_topology_synoptic_passion_v1.json"
BUILD = ROOT / "scripts/build_bible_topology_synoptic_passion_seed_v1.py"
VALIDATE = ROOT / "scripts/validate_bible_topology_contrib_shard_v1.py"


def test_passion_seed_validates_tier_a() -> None:
    proc = subprocess.run(
        [
            PY,
            str(VALIDATE.relative_to(ROOT)),
            "--json",
            str(PASSION_SEED.relative_to(ROOT)),
            "--min-edges",
            "3",
            "--max-edges",
            "500",
            "--stdout-only",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout.strip())
    assert doc["validation_ok"] is True
    assert doc["edge_count"] >= 80


def test_build_passion_seed_reproduces() -> None:
    proc = subprocess.run(
        [PY, str(BUILD.relative_to(ROOT))],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert PASSION_SEED.is_file()
    doc = json.loads(PASSION_SEED.read_text(encoding="utf-8-sig"))
    assert doc["slice_id"] == "SYNOPTIC_PASSION_WEEK_v1"
    assert doc["tier"] == "A"
    assert doc["edge_count"] == len(doc["edges"])


def test_parallel_duplicate_direction_fails() -> None:
    bad = {
        "schema": "bible_topology_shard_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "slice_id": "SYNOPTIC_PASSION_WEEK_v1",
        "tier": "A",
        "edge_count": 2,
        "edge_budget_max": 500,
        "provenance_ref": "tests/fixtures/bible_topology/DATA_PROVENANCE.md#tier-a-synoptic-passion-v1",
        "labels": ["contributor_provided", "research_only", "bible_topology_shard_v1"],
        "edges": [
            {
                "src_ref": "MAT.26.36",
                "dst_ref": "MRK.14.32",
                "relation": "parallel",
                "contributor_provided": True,
                "customer_provided": False,
                "source_note": "duplicate direction test row one",
            },
            {
                "src_ref": "MRK.14.32",
                "dst_ref": "MAT.26.36",
                "relation": "parallel",
                "contributor_provided": True,
                "customer_provided": False,
                "source_note": "duplicate direction test row two",
            },
        ],
    }
    tmp = ROOT / "reports/_tmp_bible_topology_bad_v1.json"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(bad), encoding="utf-8")
    try:
        proc = subprocess.run(
            [
                PY,
                str(VALIDATE.relative_to(ROOT)),
                "--json",
                str(tmp.relative_to(ROOT)),
                "--min-edges",
                "1",
                "--max-edges",
                "500",
                "--stdout-only",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode != 0
    finally:
        if tmp.is_file():
            tmp.unlink()
