# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "auto_enrich_sasang_from_literature_stub_v1.py"


def test_auto_enrich_single_and_ambiguous(tmp_path):
    cat = tmp_path / "c.jsonl"
    catalog_rows = [
        {
            "schema": "sasang_saju_literature_catalog_row_v1",
            "pmid": "111",
            "title": "Paper A",
            "abstractText": "We study Tae-Eum Sasang type in healthy adults.",
        },
        {
            "schema": "sasang_saju_literature_catalog_row_v1",
            "pmid": "222",
            "title": "Paper B",
            "abstractText": "So-Yang and So-Eum types were compared.",
        },
    ]
    cat.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in catalog_rows) + "\n", encoding="utf-8")

    stubs = tmp_path / "s.jsonl"
    stub_rows = [
        {
            "schema": "sasang_saju_joint_benchmark_row_v1",
            "person_id": "literature_pmid_111",
            "literature_catalog_pmids": ["111"],
            "literature_catalog_snapshot": {"title": "Paper A"},
            "benchmark_tier": "pending_human_merge",
        },
        {
            "schema": "sasang_saju_joint_benchmark_row_v1",
            "person_id": "literature_pmid_222",
            "literature_catalog_pmids": ["222"],
            "literature_catalog_snapshot": {"title": "Paper B"},
            "benchmark_tier": "pending_human_merge",
        },
    ]
    stubs.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in stub_rows) + "\n", encoding="utf-8")
    out = tmp_path / "o.jsonl"
    p = subprocess.run(
        [sys.executable, str(_SCRIPT), "--stubs", str(stubs), "--catalog", str(cat), "--out", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr + p.stdout
    lines = [json.loads(ln) for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines[0]["literature_sasang_extract"]["state"] == "single_type"
    assert lines[0]["sasang_constitution"]["label_en"] == "Tae-Eum"
    assert lines[0].get("birth_resolution") is None
    assert lines[1]["literature_sasang_extract"]["state"] == "ambiguous_multi_type"
    assert lines[1]["sasang_constitution"] is None
