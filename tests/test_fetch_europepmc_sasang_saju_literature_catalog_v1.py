# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "fetch_europepmc_sasang_saju_literature_catalog_v1.py"
_FIXTURE = _ROOT / "tests" / "fixtures" / "europepmc_sasang_search_minimal_v1.json"


def test_cli_fixture_writes_jsonl(tmp_path):
    out = tmp_path / "cat.jsonl"
    man = tmp_path / "man.json"
    p = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--fixture",
            str(_FIXTURE),
            "--max-total",
            "10",
            "--out",
            str(out),
            "--manifest",
            str(man),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr + p.stdout
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row.get("schema") == "sasang_saju_literature_catalog_row_v1"
    assert row.get("pmid") == "12345678"
    doc = json.loads(man.read_text(encoding="utf-8"))
    assert doc.get("schema") == "sasang_saju_literature_catalog_manifest_v1"
    assert doc.get("mode") == "fixture"
