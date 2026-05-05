# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "build_sasang_saju_joint_review_queue_from_catalog_v1.py"


def test_build_queue_from_fixture_catalog(tmp_path):
    inp = tmp_path / "cat.jsonl"
    rows = [
        {
            "schema": "sasang_saju_literature_catalog_row_v1",
            "pmid": "99990001",
            "title": "Sasang cohort fixture",
            "pubYear": "2024",
            "europepmc_url": "https://europepmc.org/article/MED/99990001",
            "relevance_tier": "high",
            "relevance_score": 5.0,
        }
    ]
    inp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    out_csv = tmp_path / "q.csv"
    out_jsonl = tmp_path / "s.jsonl"
    p = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--in",
            str(inp),
            "--out-csv",
            str(out_csv),
            "--out-jsonl",
            str(out_jsonl),
            "--max-rows",
            "10",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr + p.stdout
    with out_csv.open(encoding="utf-8", newline="") as f:
        r = list(csv.DictReader(f))
    assert len(r) == 1
    assert r[0]["pmid"] == "99990001"
    jl = [json.loads(ln) for ln in out_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert jl[0]["person_id"] == "literature_pmid_99990001"
    assert jl[0]["literature_catalog_pmids"] == ["99990001"]
