#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOSPI HD delegation: flow gate + fallback A/B + July OOS prep [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/kospi_hd_delegation_flow_gate_chain_v1_latest.json"
PY = sys.executable


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, optional: bool = False) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    row = {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "optional": optional,
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-500:],
    }
    return row


def _as_of_default() -> str:
    from scripts.kospi_krx_calendar_v1 import last_krx_trading_day_on_or_before

    today = date.today().isoformat()
    return last_krx_trading_day_on_or_before(date.fromisoformat(today)) or today


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--output", type=Path, default=OUT)
    ns = ap.parse_args()
    as_of = ns.as_of_kst or _as_of_default()

    steps: list[dict[str, Any]] = []
    steps.append(_run("pytest_flow_gate", [PY, "-m", "pytest", "tests/test_kospi_forward_flow_gate_lib_v1.py", "-q"]))
    steps.append(
        _run(
            "parallel_june",
            [
                PY,
                "scripts/build_kospi_june2026_parallel_shadow_bundle_v1.py",
                "--year-month",
                "2026-06",
                "--as-of-kst",
                as_of,
            ],
        )
    )
    steps.append(_run("cpcv", [PY, "scripts/build_kospi_cpcv_shadow_promotion_poc_v1.py", "--as-of-kst", as_of]))
    steps.append(
        _run(
            "fallback_ab_june",
            [
                PY,
                "scripts/build_kospi_composite_fallback_ab_v1.py",
                "--year-month",
                "2026-06",
                "--as-of-kst",
                as_of,
            ],
        )
    )
    steps.append(
        _run(
            "july_calendar_eval",
            [
                PY,
                "scripts/build_kospi_june2026_daily_prophecy_calendar_v1.py",
                "--year-month",
                "2026-07",
                "--skip-panel-rebuild",
            ],
        )
    )
    steps.append(
        _run(
            "july_eval",
            [
                PY,
                "scripts/eval_kospi_june2026_daily_prophecy_v1.py",
                "--calendar-json",
                "reports/kospi_202607_daily_prophecy_calendar_v1.json",
                "--as-of-kst",
                as_of,
            ],
        )
    )
    steps.append(
        _run(
            "july_oos_chain",
            [PY, "scripts/run_kospi_july_oos_shadow_chain_v1.py", "--year-month", "2026-07", "--as-of-kst", as_of],
        )
    )
    steps.append(
        _run(
            "drill_july_csv",
            [
                PY,
                "scripts/export_kospi_composite_shadow_daily_drill_v1.py",
                "--year-month",
                "2026-07",
                "--output-csv",
                "reports/kospi_202607_composite_shadow_daily_drill_v1.csv",
            ],
        )
    )
    steps.append(
        _run(
            "stochastic_sensitivity",
            [
                PY,
                "scripts/build_kospi_forward_flow_stochastic_sensitivity_v1.py",
                "--from-month",
                "2027-01",
                "--to-month",
                "2028-12",
                "--n-paths",
                "30",
                "--seed",
                "42",
            ],
            optional=True,
        )
    )

    required_fail = [s for s in steps if not s.get("optional") and s["exit_code"] != 0]
    ab = {}
    ab_path = ROOT / "reports/kospi_composite_fallback_ab_v1_latest.json"
    if ab_path.is_file():
        ab = json.loads(ab_path.read_text(encoding="utf-8-sig"))
    july_ready = {}
    jp = ROOT / "reports/kospi_july_forward_oos_readiness_v1_latest.json"
    if jp.is_file():
        july_ready = json.loads(jp.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "kospi_hd_delegation_flow_gate_chain_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "as_of_kst": as_of,
        "quality_ok": len(required_fail) == 0,
        "steps": steps,
        "fallback_ab": {
            "n_scored": ab.get("n_scored_days"),
            "soft_delta_bear_conditional": (ab.get("soft_delta_vs_active") or {}).get("composite_bear_conditional"),
            "soft_delta_active_hold": (ab.get("soft_delta_vs_active") or {}).get("composite_active_hold"),
        },
        "july_oos": {
            "n_scored": july_ready.get("n_scored"),
            "status": july_ready.get("status"),
        },
        "long_horizon_policy_ko": "2027-2028 outlook headline 제외 — July OOS + June CPCV만 승인 근거",
        "reproduce": f"py scripts/run_kospi_hd_delegation_flow_gate_chain_v1.py --as-of-kst {as_of}",
    }
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_hd_delegation_flow_gate_chain_v1_latest.json"
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": len(required_fail) == 0, "quality_ok": doc["quality_ok"], "as_of": as_of}, ensure_ascii=False))
    return 1 if required_fail else 0


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
