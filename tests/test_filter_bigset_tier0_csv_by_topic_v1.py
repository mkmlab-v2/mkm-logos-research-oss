"""Topic strict filter for BigSet tier0 CSV."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILTER = ROOT / "scripts/filter_bigset_tier0_csv_by_topic_v1.py"


def test_strict_nephilim_drops_sons_of_god_group(tmp_path: Path):
    csv_path = tmp_path / "nephilim.csv"
    csv_path.write_text(
        "source_url,tradition,scholar_school,corpus_tier,verse_ref,excerpt,"
        "retrieval_timestamp_utc,conflict_group_id,school_tier,interpretation_ko,citation_lock_anchor\n"
        "https://live.example/neph,N,T,B,Gen.6.4,nephilim watchers,2026-06-24T00:00:00Z,"
        "MKM_CONCEPT_NEPHILIM,historical_criticism,ko,https://live.example/neph\n"
        "https://live.example/sons,N,T,B,Gen.6.1,sons of god only,2026-06-24T00:00:01Z,"
        "MKM_CONCEPT_SONS_OF_GOD,historical_criticism,ko2,https://live.example/sons\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(FILTER),
            "--csv",
            str(csv_path),
            "--topic-slug",
            "nephilim_watcher_cross_refs",
            "--strict",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["conflict_group_id"] == "MKM_CONCEPT_NEPHILIM"
