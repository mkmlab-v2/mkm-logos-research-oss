from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "scripts/run_p0_p1_p2_hybrid_batch_v1.py"
OUT = ROOT / "reports/p0_p1_p2_hybrid_batch_v1_latest.json"
PILOT = ROOT / "reports/btrack_swarm_tier_a_pilot_v1_latest.json"
P1 = ROOT / "reports/p1_advisory_ops_wiring_v1_latest.json"


def test_p0_p1_p2_hybrid_batch_runs() -> None:
    rc = subprocess.call([sys.executable, str(BATCH)], cwd=str(ROOT))
    assert rc == 0
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "p0_p1_p2_hybrid_batch_v1"
    assert doc["ok"] is True
    assert doc["p3_hard_lock"]["track_a_promotion_approved"] is False
    assert doc["p3_hard_lock"]["final_call_auto_merge"] is False
    assert PILOT.is_file()
    assert P1.is_file()
    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    assert pilot["min_krx_weekday_rows"] == 15
    assert pilot["gate_mode"] == "warning"
    p1 = json.loads(P1.read_text(encoding="utf-8"))
    assert p1["excluded_from_final_call"] is True
