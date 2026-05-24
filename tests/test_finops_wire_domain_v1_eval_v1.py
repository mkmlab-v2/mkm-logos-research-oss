"""FinOps domain v1 eval contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "reports/finops_wire_domain_v1_eval_latest.json"


def test_finops_domain_eval_runs_and_trading_gates():
    cp = subprocess.run(
        [sys.executable, "scripts/run_finops_wire_domain_v1_eval_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr[-500:]
    doc = json.loads(EVAL.read_text(encoding="utf-8"))
    assert doc.get("ok") is True
    assert doc.get("primary_scenario") == "trading"
    gates = doc.get("gates") or {}
    assert gates.get("packet_roundtrip_ok") is True
    assert gates.get("no_empty_trading_turns") is True
