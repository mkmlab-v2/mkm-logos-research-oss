"""BigSet tier0 CSV accumulate merge + dry-run accumulate chain."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.merge_bigset_tier0_csv_accumulate_v1 import merge_accumulate

MERGE = ROOT / "scripts/merge_bigset_tier0_csv_accumulate_v1.py"
CHAIN = ROOT / "scripts/run_bigset_live_row_accumulate_chain_v1.py"
FIXTURE_A = ROOT / "tests/fixtures/bigset/atypical_island_demo_tier0_v1.csv"
FIXTURE_B = ROOT / "tests/fixtures/bigset/sample_theology_tier0_rows_v1.csv"


def test_merge_appends_new_source_url(tmp_path: Path):
    target = tmp_path / "acc.csv"
    target.write_text(
        "source_url,tradition,scholar_school,corpus_tier,verse_ref,excerpt,"
        "retrieval_timestamp_utc,conflict_group_id,school_tier,interpretation_ko,citation_lock_anchor\n"
        "https://example.org/existing/,T,s,B,Gen.1.1,x,2026-06-24T00:00:00Z,G,historical_criticism,ko,https://example.org/existing/\n",
        encoding="utf-8",
    )
    batch = tmp_path / "batch.csv"
    batch.write_text(
        "source_url,tradition,scholar_school,corpus_tier,verse_ref,excerpt,"
        "retrieval_timestamp_utc,conflict_group_id,school_tier,interpretation_ko,citation_lock_anchor\n"
        "https://example.org/new/,T,s,B,Gen.2.1,y,2026-06-24T00:00:01Z,G,judaic_mysticism,ko2,https://example.org/new/\n",
        encoding="utf-8",
    )
    result = merge_accumulate(target_csv=target, batch_csv=batch)
    assert result["ok"] is True
    assert result["rows_appended"] == 1
    assert result["rows_after"] == 2


def test_merge_skips_duplicate_source_url(tmp_path: Path):
    target = tmp_path / "acc.csv"
    url = "https://example.org/same/"
    target.write_text(
        "source_url,tradition,scholar_school,corpus_tier,verse_ref,excerpt,"
        "retrieval_timestamp_utc,conflict_group_id,school_tier,interpretation_ko,citation_lock_anchor\n"
        f"{url},T,s,B,Gen.1.1,x,2026-06-24T00:00:00Z,G,historical_criticism,ko,{url}\n",
        encoding="utf-8",
    )
    batch = tmp_path / "batch.csv"
    batch.write_text(
        "source_url,tradition,scholar_school,corpus_tier,verse_ref,excerpt,"
        "retrieval_timestamp_utc,conflict_group_id,school_tier,interpretation_ko,citation_lock_anchor\n"
        f"https://example.org/same,T,s,B,Gen.9.9,z,2026-06-24T00:00:02Z,G,judaic_mysticism,ko2,https://example.org/same\n",
        encoding="utf-8",
    )
    result = merge_accumulate(target_csv=target, batch_csv=batch)
    assert result["rows_appended"] == 0
    assert result["rows_after"] == 1
    assert result["skipped_duplicate_source_urls"]


def test_accumulate_chain_dry_run_batch(tmp_path: Path):
    proc = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--dry-run-batch",
            str(FIXTURE_A),
            "--topic-slug",
            "accumulate_pytest_tmp",
            "--skip-ingest",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    csv_out = ROOT / "docs/research/raw/bigset_accumulate_pytest_tmp_tier0_v1.csv"
    assert csv_out.is_file()
    with csv_out.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 3
