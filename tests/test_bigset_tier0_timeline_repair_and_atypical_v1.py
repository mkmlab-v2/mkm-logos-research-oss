"""BigSet timeline repair + atypical signal detector."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.detect_bigset_tier0_atypical_signal_v1 import detect
from scripts.repair_bigset_tier0_timeline_order_v1 import repair_rows

REPAIR = ROOT / "scripts/repair_bigset_tier0_timeline_order_v1.py"
ATYPICAL = ROOT / "scripts/detect_bigset_tier0_atypical_signal_v1.py"
FIXTURE = ROOT / "tests/fixtures/bigset/sample_theology_tier0_rows_v1.csv"


def _fieldnames() -> list[str]:
    with FIXTURE.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f).fieldnames or [])


def test_repair_fixes_inversion(tmp_path: Path):
    bad = tmp_path / "inverted.csv"
    fieldnames = [
        "source_url",
        "tradition",
        "scholar_school",
        "corpus_tier",
        "verse_ref",
        "excerpt",
        "retrieval_timestamp_utc",
        "conflict_group_id",
        "school_tier",
        "interpretation_ko",
        "citation_lock_anchor",
    ]
    rows = [
        {
            "source_url": "https://example.org/a",
            "tradition": "T",
            "scholar_school": "s",
            "corpus_tier": "B",
            "verse_ref": "Gen.6.4",
            "excerpt": "x",
            "retrieval_timestamp_utc": "2026-06-24T00:00:00Z",
            "conflict_group_id": "G1",
            "school_tier": "historical_criticism",
            "interpretation_ko": "해석",
            "citation_lock_anchor": "https://example.org/a",
        },
        {
            "source_url": "https://example.org/b",
            "tradition": "T",
            "scholar_school": "s",
            "corpus_tier": "B",
            "verse_ref": "Gen.6.1",
            "excerpt": "y",
            "retrieval_timestamp_utc": "2026-06-24T00:00:01Z",
            "conflict_group_id": "G1",
            "school_tier": "judaic_mysticism",
            "interpretation_ko": "해석",
            "citation_lock_anchor": "https://example.org/b",
        },
    ]
    with bad.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    repaired, meta = repair_rows(rows)
    assert meta["inversions_before"] == 1
    assert meta["inversions_after"] == 0
    assert meta["gate_ok_after"] is True

    out = tmp_path / "repaired.csv"
    proc = subprocess.run(
        [sys.executable, str(REPAIR), "--csv", str(bad), "--out-csv", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert out.is_file()


def test_atypical_detects_school_island():
    rows = [
        {
            "verse_ref": "Gen.6.1",
            "conflict_group_id": "G1",
            "school_tier": "historical_criticism",
        },
        {
            "verse_ref": "Gen.6.2",
            "conflict_group_id": "G1",
            "school_tier": "judaic_mysticism",
        },
        {
            "verse_ref": "Gen.6.3",
            "conflict_group_id": "G1",
            "school_tier": "historical_criticism",
        },
    ]
    doc = detect(rows)
    assert doc["signal_count"] >= 1
    assert any(s["signal_type"] == "school_tier_island" for s in doc["signals"])


def test_atypical_cli_exit_zero(tmp_path: Path):
    proc = subprocess.run(
        [sys.executable, str(ATYPICAL), "--csv", str(FIXTURE), "--out", str(tmp_path / "sig.json")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
