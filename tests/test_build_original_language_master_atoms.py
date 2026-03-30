from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.core.build_original_language_master_atoms import main


def test_build_original_language_master_atoms_outputs(tmp_path: Path) -> None:
    out_jsonl = tmp_path / "atoms.jsonl"
    out_summary = tmp_path / "atoms_summary.json"
    old = sys.argv
    try:
        sys.argv = [
            "build_original_language_master_atoms.py",
            "--out-jsonl",
            str(out_jsonl),
            "--out-summary",
            str(out_summary),
        ]
        rc = main()
    finally:
        sys.argv = old
    assert rc == 0
    assert out_jsonl.is_file()
    assert out_summary.is_file()
    summary = json.loads(out_summary.read_text(encoding="utf-8"))
    assert summary["schema"] == "original_language_master_atoms_summary_v1"
    assert int(summary["stats"]["unique_master_atoms"]) > 0


def test_build_original_language_master_atoms_heuristic_mode(tmp_path: Path) -> None:
    out_jsonl = tmp_path / "atoms_v2.jsonl"
    out_summary = tmp_path / "atoms_summary_v2.json"
    old = sys.argv
    try:
        sys.argv = [
            "build_original_language_master_atoms.py",
            "--out-jsonl",
            str(out_jsonl),
            "--out-summary",
            str(out_summary),
            "--lemma-mode",
            "heuristic_lemma_v2",
        ]
        rc = main()
    finally:
        sys.argv = old
    assert rc == 0
    summary = json.loads(out_summary.read_text(encoding="utf-8"))
    assert summary["stats"]["lemma_method"] == "heuristic_lemma_v2"
