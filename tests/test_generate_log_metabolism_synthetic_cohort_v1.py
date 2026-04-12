# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_generate_synthetic_and_validate_metabolism(tmp_path: Path) -> None:
    out = tmp_path / "syn.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "generate_log_metabolism_synthetic_cohort_v1.py"),
            "--rows",
            "40",
            "--seed",
            "7",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert r.returncode == 0, r.stderr
    lines = [x for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 40
    from scripts.ingest_notebooklm_metabolism_jsonl import parse_and_validate_metabolism_jsonl

    rows, errs = parse_and_validate_metabolism_jsonl(out.read_text(encoding="utf-8"))
    assert not errs
    assert len(rows) == 40
