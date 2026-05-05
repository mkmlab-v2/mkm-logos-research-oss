# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "filter_sasang_saju_literature_catalog_v1.py"


def test_filter_min_tier_medium(tmp_path):
    inp = tmp_path / "in.jsonl"
    rows = [
        {
            "schema": "sasang_saju_literature_catalog_row_v1",
            "pmid": "1",
            "title": "Squid Game characters and Sasang SPQ",
            "abstractText": "Netflix drama fictional character ratings.",
        },
        {
            "schema": "sasang_saju_literature_catalog_row_v1",
            "pmid": "2",
            "title": "SCAT and Sasang constitutional types in healthy volunteers",
            "abstractText": "We classified Korean medicine Sasang constitutional type using SCAT in a cohort of adults.",
        },
    ]
    inp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    out = tmp_path / "out.jsonl"
    p = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--in",
            str(inp),
            "--out",
            str(out),
            "--min-tier",
            "medium",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr + p.stdout
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    doc = json.loads(lines[0])
    assert doc["pmid"] == "2"
    assert doc.get("relevance_tier") in ("medium", "high")
