"""P17 gold router q05 align — promote gold prefix first."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GOLD_EVAL = ROOT / "reports/logos_gold_query_eval_v1_latest.json"
ROUTER_Q05 = ROOT / "reports/magic_orb_insight_by_query/router_q05_latest.json"


@pytest.fixture(scope="module")
def p17_chain() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_gold_router_q05_align_p17_chain_v1.py", "--skip-pytest"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_q05_router_hit_at_one(p17_chain: None) -> None:
    gold = json.loads(GOLD_EVAL.read_text(encoding="utf-8-sig"))
    row = next(r for r in gold["rows"] if r["id"] == "q05")
    assert row["hit_at_k"]["1"]["router"] is True
    assert row["gate_pass"] is True


def test_q05_promote_gold_prefix_meta(p17_chain: None) -> None:
    router = json.loads(ROUTER_Q05.read_text(encoding="utf-8"))
    meta = router.get("materialize_meta") or {}
    assert meta.get("promote_gold_prefix_first") is True
    top = (router.get("verse_ids") or [""])[0]
    assert top.startswith("Rev.18")


def test_gold_required_all_pass(p17_chain: None) -> None:
    gold = json.loads(GOLD_EVAL.read_text(encoding="utf-8-sig"))
    assert gold["summary"]["gold_required_all_pass"] is True
