"""Crosswalk gold q10–q12 materialize smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_logos_gold_crosswalk_queries_v1.py"
GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"
REPORT_DIR = ROOT / "reports/magic_orb_insight_by_query"


def test_materialize_logos_gold_crosswalk_queries_v1():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    for qid in ("q10", "q11", "q12"):
        router = json.loads((REPORT_DIR / f"router_{qid}_latest.json").read_text(encoding="utf-8"))
        item = next(x for x in json.loads(GOLD.read_text(encoding="utf-8"))["items"] if x["id"] == qid)
        gold_ids = set(item.get("gold_verse_ids") or [])
        router_ids = set(router.get("verse_ids") or [])
        assert gold_ids <= router_ids or router_ids & gold_ids
        for vid in router.get("verse_ids") or []:
            assert not str(vid).startswith("verse_ref:")
            assert not str(vid).startswith("hebrew::")
