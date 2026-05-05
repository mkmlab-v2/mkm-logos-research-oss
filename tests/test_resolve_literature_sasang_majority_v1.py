# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "resolve_literature_sasang_majority_v1.py"


def test_majority_resolves_ambiguous(tmp_path):
    cat = tmp_path / "c.jsonl"
    cat.write_text(
        json.dumps(
            {
                "schema": "sasang_saju_literature_catalog_row_v1",
                "pmid": "1",
                "title": "X",
                "abstractText": "Tae-Eum type and Tae-Eum Sasang and Tae-Eum obesity vs one So-Yang mention.",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    inp = tmp_path / "i.jsonl"
    row = {
        "schema": "sasang_saju_joint_benchmark_row_v1",
        "person_id": "literature_pmid_1",
        "literature_catalog_pmids": ["1"],
        "literature_catalog_snapshot": {"title": "X"},
        "literature_sasang_extract": {"state": "ambiguous_multi_type"},
        "sasang_constitution": None,
    }
    inp.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    out = tmp_path / "o.jsonl"
    p = subprocess.run(
        [sys.executable, str(_SCRIPT), "--in", str(inp), "--out", str(out), "--catalog", str(cat)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr + p.stdout
    doc = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert doc["literature_sasang_extract"]["state"] == "resolved_majority_v1"
    assert doc["sasang_constitution"]["label_en"] == "Tae-Eum"


def test_promote_curated_csv_dry_run(tmp_path):
    csvp = tmp_path / "q.csv"
    csvp.write_text(
        "pmid,pubYear,title,europepmc_url,relevance_tier,relevance_score,birth_instant_utc,iana_tz,is_male,sasang_label_ko,sasang_label_en,quote_from_paper,curator_ok,notes\n"
        "9,2020,T,,,,1990-01-01T00:00:00Z,UTC,y,태음인,Tae-Eum,fixture,y,\n",
        encoding="utf-8",
    )
    tgt = tmp_path / "t.jsonl"
    p = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "promote_joint_curated_csv_v1.py"),
            "--csv",
            str(csvp),
            "--target-jsonl",
            str(tgt),
            "--dry-run",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr + p.stdout
    raw = p.stdout.strip()
    summary = json.loads(raw[raw.index("{") :])
    assert summary.get("would_append") == 1
