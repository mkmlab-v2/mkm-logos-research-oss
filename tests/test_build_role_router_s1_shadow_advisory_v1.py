"""Regression: role router S1 shadow advisory snapshot (non-gating)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_role_router_s1_shadow_advisory_v1.py"


def _run(tmp: Path, router: dict, weekly: dict, gate: dict) -> subprocess.CompletedProcess[str]:
    (tmp / "router.json").write_text(json.dumps(router, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (tmp / "weekly.json").write_text(json.dumps(weekly, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (tmp / "gate.json").write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_latest = tmp / "advisory_latest.json"
    out_log = tmp / "advisory_log.jsonl"
    router = tmp / "router.json"
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--router-json",
        str(router),
        "--weekly-json",
        str(tmp / "weekly.json"),
        "--gate-json",
        str(tmp / "gate.json"),
        "--out-latest",
        str(out_latest),
        "--out-log",
        str(out_log),
    ]
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)


def test_advisory_schema_and_false_intervention(tmp_path: Path) -> None:
    router = {
        "schema": "prophecy_role_router_multiscenario_opt_v1",
        "best_candidate": {
            "params": {"a": 1},
            "oos_metrics": {
                "n_days": 30,
                "directional_hit_rate_active": 0.6,
                "mdd": -0.1,
                "sharpe": 0.5,
            },
        },
        "top_candidates": [],
    }
    weekly = {"summary": {"strict_gap": 0.05}}
    gate_hold = {"decision": "HOLD"}
    cp = _run(tmp_path, router, weekly, gate_hold)
    assert cp.returncode == 0, cp.stderr
    latest = json.loads((tmp_path / "advisory_latest.json").read_text(encoding="utf-8"))
    assert latest["schema"] == "role_router_s1_shadow_advisory_v1"
    row = latest["last_row"]
    assert row["router_stance"] == "PROPOSE_RELAX_OR_ALLOW"
    assert row["baseline_stance"] == "CONSERVATIVE_HOLD"
    assert row["metrics"]["false_intervention_proxy"] == 1.0


def test_agreement_conservative(tmp_path: Path) -> None:
    router = {
        "schema": "prophecy_role_router_multiscenario_opt_v1",
        "best_candidate": {
            "params": {},
            "oos_metrics": {
                "n_days": 30,
                "directional_hit_rate_active": 0.4,
                "mdd": -0.2,
                "sharpe": -0.1,
            },
        },
        "top_candidates": [],
    }
    weekly = {"summary": {"strict_gap": 0.2}}
    gate = {"decision": "HOLD"}
    cp = _run(tmp_path, router, weekly, gate)
    assert cp.returncode == 0
    row = json.loads((tmp_path / "advisory_latest.json").read_text(encoding="utf-8"))["last_row"]
    assert row["metrics"]["conflict_resolution_proxy"] == 1.0
    assert row["metrics"]["false_intervention_proxy"] == 0.0
