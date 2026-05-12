#!/usr/bin/env python3
"""Triage: B-track price prophecy chain — script paths, OHLCV inputs, key artifacts.

Read-only. Does not call yfinance or rebuild scores. Use after clone or before
run_btrack_daily_hypothesis_chain / monthly runners to see gaps.

Exit: 0 always unless --strict (then 1 if any required script or KOSPI CSV missing).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_chain_prereqs_v1_latest.json"
SCHEMA = "btrack_prophecy_chain_prereqs_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _check_path(kind: str, path: Path, required: bool) -> dict[str, Any]:
    ok = path.is_file()
    return {
        "kind": kind,
        "path": _rel(path),
        "required": required,
        "ok": ok,
        "note": None if ok else ("missing" if required else "optional_missing"),
    }


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _dual_leg_hint(score: dict[str, Any] | None) -> dict[str, Any] | None:
    if not score:
        return None
    rows = score.get("rows")
    if not isinstance(rows, list) or not rows:
        return {"status": "no_rows", "eval_dates_with_both_legs": 0, "eval_dates_total": 0}
    by_date: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        if not isinstance(r, dict):
            continue
        ed = str(r.get("eval_date") or "").strip()
        ins = str(r.get("instrument") or "").strip().lower()
        if ed and ins:
            by_date[ed].add(ins)
    total = len(by_date)
    both = sum(1 for legs in by_date.values() if {"kospi", "btc"} <= legs)
    return {
        "status": "ok" if total and both == total else "partial_or_single_leg",
        "eval_dates_total": total,
        "eval_dates_with_both_legs": both,
        "hint": "instrument combo walkforward needs kospi+btc per eval_date; use --force-dual-leg-panel with both CSVs when hypothesis is single-leg.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT, help="Write JSON report (skipped with --stdout-only).")
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if a required script or KOSPI SSOT CSV is missing.",
    )
    args = ap.parse_args()
    root: Path = args.workspace_root.resolve()

    scripts_req = [
        "scripts/run_btrack_daily_hypothesis_chain.ps1",
        "scripts/build_btrack_prophecy_score_from_ohlcv.py",
        "scripts/eval_prophecy_hit_rate_v1.py",
        "scripts/run_prophecy_per_date_combo_walkforward_v1.py",
        "scripts/run_prophecy_instrument_combo_walkforward_v1.py",
        "scripts/eval_prophecy_promotion_gates_v1.py",
        "scripts/fast_promotion_gate_v1.py",
        "scripts/build_prophecy_health_status_v1.py",
        "scripts/check_prophecy_proxy_streak_gate_v1.py",
        "scripts/run_waiting_queue_monthly_check.ps1",
    ]
    scripts_opt = [
        "scripts/generate_btrack_hypothesis_prophecy_v1.py",
        "scripts/run_btrack_prophecy_contemplation_v1.py",
        "scripts/run_prophecy_restoration_spike.py",
        "scripts/eval_btrack_prophecy_post_mortem_v1.py",
        "scripts/Invoke-MaxProphecyBurst_v1.ps1",
    ]

    kospi = root / "research" / "market_data" / "kospi_daily_external_yf.csv"
    btc = root / "research" / "market_data" / "btc_daily_external_yf.csv"

    artifacts = [
        ("btrack_hypothesis_prophecy_latest.json", False),
        ("btrack_prophecy_score_latest.json", False),
        ("prophecy_hit_rate_eval_latest.json", False),
        ("prophecy_per_date_combo_walkforward_v1_latest.json", False),
        ("prophecy_instrument_combo_walkforward_v1_latest.json", False),
        ("prophecy_promotion_gates_v1_latest.json", False),
        ("fast_promotion_gate_v1_latest.json", False),
        ("prophecy_health_status_latest.json", False),
        ("general_prophecy_latest.json", False),
    ]
    monthly_glob = list((root / "docs" / "final" / "artifacts").glob("prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"))

    checks: list[dict[str, Any]] = []
    for rel in scripts_req:
        checks.append(_check_path("script", root / rel, True))
    for rel in scripts_opt:
        checks.append(_check_path("script_optional", root / rel, False))
    checks.append(_check_path("data", kospi, True))
    checks.append(_check_path("data", btc, False))

    art_dir = root / "docs" / "final" / "artifacts"
    for name, _ in artifacts:
        checks.append(_check_path("artifact", art_dir / name, False))

    checks.append(
        {
            "kind": "artifact_monthly",
            "path": _rel(monthly_glob[0]) if monthly_glob else "docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json",
            "required": False,
            "ok": bool(monthly_glob),
            "note": "present" if monthly_glob else "optional_missing",
        }
    )

    score_path = art_dir / "btrack_prophecy_score_latest.json"
    score_doc = _load_json(score_path)
    inputs = (score_doc or {}).get("inputs") if score_doc else None
    dual = _dual_leg_hint(score_doc)

    summary = {
        "scripts_required_ok": all(c["ok"] for c in checks if c["kind"] == "script" and c.get("required")),
        "kospi_csv_ok": kospi.is_file(),
        "btc_csv_ok": btc.is_file(),
        "artifacts_present": sum(1 for c in checks if c["kind"] == "artifact" and c["ok"]),
        "artifacts_total": sum(1 for c in checks if c["kind"] == "artifact"),
    }

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "workspace_root": _rel(root),
        "summary": summary,
        "score_inputs_snapshot": inputs if isinstance(inputs, dict) else None,
        "instrument_combo_dual_leg": dual,
        "checks": checks,
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.stdout_only:
        sys.stdout.write(text)
    else:
        out = args.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"WROTE: {out}", file=sys.stderr)

    if args.strict:
        if not summary["scripts_required_ok"] or not summary["kospi_csv_ok"]:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
