#!/usr/bin/env python3
"""Ops dynamical full ladder L0→L4 chain [HYPO · B-track · send_gate HOLD]."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/ops_dynamical_full_ladder_chain_v1_latest.json"

STEPS: list[tuple[str, list[str]]] = [
    ("L0_bench", [sys.executable, "scripts/run_ops_dynamical_bench_v1.py"]),
    ("L1_eval", [sys.executable, "scripts/run_ops_dynamical_l1_eval_v1.py", "--no-patch-bench-latest"]),
    (
        "L2_intervention_synthetic",
        [
            sys.executable,
            "scripts/run_ops_dynamical_l2_intervention_chain_v1.py",
            "--mode",
            "synthetic",
            "--jsonl",
            "reports/ops_dynamical_timeseries_l2_smoke_v1.jsonl",
            "--out",
            "reports/ops_dynamical_l2_intervention_chain_smoke_v1_latest.json",
        ],
    ),
    ("L2_eval", [sys.executable, "scripts/run_ops_dynamical_l2_eval_v1.py"]),
    ("L3_cross_fixture", [sys.executable, "scripts/run_ops_dynamical_l3_cross_fixture_eval_v1.py"]),
    ("L4_clinical", [sys.executable, "scripts/run_ops_dynamical_l4_clinical_eval_v1.py"]),
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    results: dict[str, Any] = {}
    ok = True
    for name, cmd in STEPS:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()
        step_ok = proc.returncode == 0
        results[name] = {"ok": step_ok, "exit_code": proc.returncode, "tail": tail[-1:] if tail else []}
        ok = ok and step_ok

    metrics: dict[str, Any] = {}
    for rel, key in [
        ("reports/ops_dynamical_l3_eval_v1_latest.json", "isomorphism_score"),
        ("reports/ops_dynamical_l4_eval_v1_latest.json", "clinical_epsilon_score"),
        ("reports/ops_dynamical_l1_eval_v1_latest.json", "stage_exact_match_rate"),
        ("reports/ops_dynamical_l2_eval_v1_latest.json", "equilibrium_restore_rate"),
    ]:
        path = ROOT / rel
        if path.is_file():
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
            metrics[key] = (doc.get("metrics") or {}).get(key)

    doc = {
        "schema": "ops_dynamical_full_ladder_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "steps": results,
        "metrics": metrics,
        "ok": ok,
        "reproduce": "py scripts/run_ops_dynamical_full_ladder_chain_v1.py",
    }
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT), "metrics": metrics}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
