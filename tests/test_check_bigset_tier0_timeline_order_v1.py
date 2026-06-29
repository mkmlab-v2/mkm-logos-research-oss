"""BigSet Tier-0 timeline ordering gate — verse monotonicity per conflict group."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_bigset_tier0_timeline_order_v1 import evaluate, parse_verse_sort_key
CHECK = ROOT / "scripts/check_bigset_tier0_timeline_order_v1.py"
FIXTURE = ROOT / "tests/fixtures/bigset/sample_theology_tier0_rows_v1.csv"
BENEI_CSV = ROOT / "docs/research/raw/bigset_benei_haelohim_cross_refs_tier0_v1.csv"


def test_parse_verse_sort_key_variants():
    assert parse_verse_sort_key("Gen.6.1-4") == (1, 6, 1)
    assert parse_verse_sort_key("Genesis 6:1-4") == (1, 6, 1)
    assert parse_verse_sort_key("Gen 6:4") == (1, 6, 4)


def test_fixture_csv_monotonic_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--csv", str(FIXTURE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_inversion_detected(tmp_path: Path):
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
            "school_tier": "historical_criticism",
            "interpretation_ko": "해석",
            "citation_lock_anchor": "https://example.org/b",
        },
    ]
    with bad.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    doc = evaluate(rows)
    assert doc["gate_ok"] is False
    assert doc["inversion_count"] == 1

    proc = subprocess.run(
        [sys.executable, str(CHECK), "--csv", str(bad)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1


def test_benei_csv_single_row_passes():
    if not BENEI_CSV.is_file():
        return
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--csv", str(BENEI_CSV)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    art = ROOT / "docs/final/artifacts/bigset_tier0_timeline_order_v1_latest.json"
    doc = json.loads(art.read_text(encoding="utf-8"))
    assert doc.get("gate_ok") is True
