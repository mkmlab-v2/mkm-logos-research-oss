"""Tests for master_atoms corpus split report script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_corpus_split_summary_keys(tmp_path: Path):
    atoms = tmp_path / "atoms.jsonl"
    atoms.write_text(
        json.dumps(
            {
                "atom_id": "hebrew::בדיקה",
                "lang": "hebrew",
                "normalized_form": "בדיקה",
                "source_files": ["verse_decoded_v2.jsonl", "dss_parsed_enriched.jsonl"],
            },
            ensure_ascii=False,
        )
        + "\n"
        + json.dumps(
            {
                "atom_id": "greek::test",
                "lang": "greek",
                "normalized_form": "test",
                "source_files": ["apocrypha_std.jsonl"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "report_master_atoms_corpus_split.py"),
            "--atoms-jsonl",
            str(atoms),
            "--out-json",
            str(out),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("schema") == "master_atoms_corpus_split_summary_v1"
    assert data["atoms_total"] == 2
    assert data["by_exclusive_pattern"].get("mixed_multi_bucket") == 1
    assert data["by_exclusive_pattern"].get("apocrypha_only") == 1
    assert data["by_bucket_presence"].get("canon_decode") == 1
    assert data["by_bucket_presence"].get("dss") == 1
