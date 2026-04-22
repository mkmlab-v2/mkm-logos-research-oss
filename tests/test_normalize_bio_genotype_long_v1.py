# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke test genotype long-format normalizer.
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "normalize_bio_genotype_long_v1.py"


def test_normalize_from_single_and_list_columns(tmp_path: Path) -> None:
    src = tmp_path / "raw.csv"
    src.write_text(
        "sample_id,rsid,rsid_list,genotype\n"
        "s1,rs1,,AA\n"
        "s1,,rs2|RS3,AA\n"
        "s2,not_rsid,rs9;bad_token,CT\n",
        encoding="utf-8",
    )
    out = tmp_path / "geno_long.csv"
    rep = tmp_path / "rep.json"
    subprocess.check_call(
        [
            sys.executable,
            str(SCRIPT),
            "--input-csv",
            str(src),
            "--output-csv",
            str(out),
            "--output-report",
            str(rep),
            "--rsid-list-col",
            "rsid_list",
        ],
        cwd=str(ROOT),
    )

    rows = list(csv.DictReader(io.StringIO(out.read_text(encoding="utf-8"))))
    assert {(r["sample_id"], r["rsid"]) for r in rows} == {
        ("s1", "rs1"),
        ("s1", "rs2"),
        ("s1", "rs3"),
        ("s2", "rs9"),
    }
    doc = json.loads(rep.read_text(encoding="utf-8"))
    assert doc.get("schema") == "bio_genotype_normalize_long_v1"
    assert int(doc["summary"]["normalized_rows"]) == 4

