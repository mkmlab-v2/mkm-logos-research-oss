"""Logos subgraph router gold eval v1 smoke ([HYPO], CPU)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/run_logos_subgraph_gold_eval_v1.py"
GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"


def test_subgraph_gold_eval_limit_one(tmp_path: Path) -> None:
    out = tmp_path / "subgraph_gold_eval.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(EVAL),
            "--gold-json",
            str(GOLD),
            "--out-json",
            str(out),
            "--limit",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_subgraph_gold_eval_v1"
    assert doc["research_only"] is True
    assert doc["send_gate"] == "HOLD"
    assert doc["repair_layer_applied"] is False
    assert doc["gpu_used"] is False
    assert len(doc["rows"]) == 1
    row = doc["rows"][0]
    assert row["metrics"]["raw"]["hit_at_k"]
    assert row["metrics"]["repair_v2"] is None
    assert "router" in row
    assert doc["summary"]["items_evaluated"] == 1


def test_subgraph_gold_eval_module_hit_helpers() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_logos_gold_query_eval_report_v1 as gold_ev

    gold_ids = ["Jer.31.33"]
    prefixes = ["Jer.31"]
    retrieved = ["Ps.89.28", "Jer.31.33", "Isa.40.1"]
    assert gold_ev._hit_at_k(retrieved, gold_ids, prefixes, 3) is True
    assert gold_ev._hit_at_k(["Ps.89.28"], gold_ids, prefixes, 1) is False
