# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "export_sasang_literature_supervised_jsonl_v1.py"


def test_export_one_row(tmp_path):
    cat = tmp_path / "c.jsonl"
    cat.write_text(
        json.dumps(
            {
                "schema": "sasang_saju_literature_catalog_row_v1",
                "pmid": "1",
                "title": "T",
                "abstractText": "Abstract body.",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    inp = tmp_path / "i.jsonl"
    row = {
        "schema": "sasang_saju_joint_benchmark_row_v1",
        "person_id": "p1",
        "literature_catalog_pmids": ["1"],
        "literature_catalog_snapshot": {"title": "T"},
        "sasang_constitution": {"label_en": "Tae-Eum", "label_ko": "태음인"},
        "benchmark_tier": "auto_literature_sasang_only",
    }
    inp.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    out = tmp_path / "o.jsonl"
    p = subprocess.run(
        [sys.executable, str(_SCRIPT), "--in", str(inp), "--catalog", str(cat), "--out", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr + p.stdout
    doc = json.loads(out.read_text(encoding="utf-8").strip())
    assert doc["label_en"] == "Tae-Eum"
    assert "Abstract body" in doc["text"]
