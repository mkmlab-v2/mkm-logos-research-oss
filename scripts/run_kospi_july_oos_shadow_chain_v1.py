#!/usr/bin/env python3
"""July OOS + composite shadow chain [HYPO][research_only]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/kospi_july_oos_shadow_chain_v1_latest.json"
PY = sys.executable
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-400:],
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-07")
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--skip-calendar-build", action="store_true")
    ap.add_argument("--output", type=Path, default=OUT)
    ns = ap.parse_args()

    if not ns.as_of_kst:
        from datetime import date

        from scripts.kospi_krx_calendar_v1 import last_krx_trading_day_on_or_before

        today = date.today().isoformat()
        ns.as_of_kst = last_krx_trading_day_on_or_before(date.fromisoformat(today)) or today

    tag = ns.year_month.replace("-", "")
    cal_path = ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json"
    steps: list[dict[str, Any]] = []

    if not ns.skip_calendar_build:
        steps.append(
            _run(
                "build_calendar",
                [
                    PY,
                    "scripts/build_kospi_june2026_daily_prophecy_calendar_v1.py",
                    "--year-month",
                    ns.year_month,
                    "--profile",
                    "v2_multilens",
                ],
            )
        )

    steps.extend(
        [
            _run(
                "eval_prophecy",
                [
                    PY,
                    "scripts/eval_kospi_june2026_daily_prophecy_v1.py",
                    "--calendar-json",
                    str(cal_path),
                    "--as-of-kst",
                    ns.as_of_kst,
                ],
            ),
            _run(
                "parallel_shadow_bundle",
                [
                    PY,
                    "scripts/build_kospi_june2026_parallel_shadow_bundle_v1.py",
                    "--year-month",
                    ns.year_month,
                    "--as-of-kst",
                    ns.as_of_kst,
                    "--calendar-json",
                    str(cal_path),
                ],
            ),
            _run(
                "july_readiness",
                [PY, "scripts/build_kospi_july_forward_oos_readiness_v1.py", "--as-of-kst", ns.as_of_kst],
            ),
            _run(
                "oos_significance",
                [
                    PY,
                    "scripts/build_kospi_june2026_oos_significance_v1.py",
                    "--year-month",
                    "2026-06",
                    "--include-july",
                ],
            ),
            _run(
                "per_date_lens_shadow_chain",
                [
                    PY,
                    "scripts/run_kospi_per_date_lens_shadow_chain_v1.py",
                    "--year-month",
                    ns.year_month,
                    "--as-of-kst",
                    ns.as_of_kst,
                    "--skip-jsonl-extend",
                    "--skip-panel-rebuild",
                ],
            ),
            _run(
                "sasang_veto_blend_shadow",
                [
                    PY,
                    "scripts/build_kospi_sasang_veto_blend_shadow_v1.py",
                    "--year-month",
                    ns.year_month,
                    "--as-of-kst",
                    ns.as_of_kst,
                ],
            ),
            _run(
                "oos_dual_hr_report",
                [
                    PY,
                    "scripts/build_kospi_oos_dual_hr_report_v1.py",
                    "--year-month",
                    ns.year_month,
                    "--as-of-kst",
                    ns.as_of_kst,
                ],
            ),
            _run(
                "per_date_weight_counterfactual_shadow",
                [
                    PY,
                    "scripts/build_kospi_per_date_weight_counterfactual_shadow_v1.py",
                    "--year-month",
                    ns.year_month,
                    "--as-of-kst",
                    ns.as_of_kst,
                ],
            ),
            _run(
                "dual_path_conflict_shadow",
                [
                    PY,
                    "scripts/build_kospi_dual_path_conflict_shadow_v1.py",
                    "--year-month",
                    ns.year_month,
                    "--as-of-kst",
                    ns.as_of_kst,
                ],
            ),
        ]
    )

    failed = [s for s in steps if s["exit_code"] != 0]
    if failed:
        print(json.dumps({"ok": False, "failed": [f["name"] for f in failed]}, ensure_ascii=False))
        return 1

    parallel_path = ROOT / f"reports/kospi_{tag}_parallel_shadow_bundle_v1_latest.json"
    if not parallel_path.is_file():
        parallel_path = ROOT / "reports/kospi_june2026_parallel_shadow_bundle_v1_latest.json"
    parallel = _read_json(parallel_path)
    readiness = _read_json(ROOT / "reports/kospi_july_forward_oos_readiness_v1_latest.json")
    dual_hr = _read_json(ROOT / f"reports/kospi_{tag}_oos_dual_hr_report_v1_latest.json")
    sasang_veto = _read_json(ROOT / f"reports/kospi_{tag}_sasang_veto_blend_shadow_v1_latest.json")
    per_date_wcf = _read_json(ROOT / f"reports/kospi_{tag}_per_date_weight_counterfactual_shadow_v1_latest.json")
    dual_path = _read_json(ROOT / f"reports/kospi_{tag}_dual_path_conflict_shadow_v1_latest.json")

    doc = {
        "schema": "kospi_july_oos_shadow_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "production_apply_authorized": False,
        "year_month": ns.year_month,
        "as_of_kst": ns.as_of_kst,
        "n_scored_july": readiness.get("n_scored"),
        "july_status": readiness.get("status"),
        "parallel_leader": parallel.get("leader_arm"),
        "dual_hr_headline": dual_hr.get("headline_ko"),
        "dual_hr_delta": dual_hr.get("delta"),
        "sasang_veto_delta": sasang_veto.get("delta_veto_minus_baseline_soft"),
        "per_date_weight_leader": per_date_wcf.get("leader_per_date_rule"),
        "per_date_weight_leader_delta_pp": per_date_wcf.get("leader_per_date_delta_pp"),
        "dual_path_bear_soft": (dual_path.get("summary") or {}).get("dual_path_bear_triple", {}).get("soft_hit_rate"),
        "dual_path_v2_soft": (dual_path.get("summary") or {}).get("dual_path_v2_router", {}).get("soft_hit_rate"),
        "dual_path_delta_vs_active": (dual_path.get("delta_vs_active_soft") or {}).get("dual_path_v2_router"),
        "steps": steps,
        "reproduce": f"py scripts/run_kospi_july_oos_shadow_chain_v1.py --year-month {ns.year_month} --as-of-kst {ns.as_of_kst}",
    }
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_july_oos_shadow_chain_v1_latest.json"
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "n_scored_july": readiness.get("n_scored"),
                "status": readiness.get("status"),
                "dual_hr": dual_hr.get("headline_ko"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
