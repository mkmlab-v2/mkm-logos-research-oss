#!/usr/bin/env python3
"""Evaluate + optional apply resolve for Logos June 2026 general_prophecy (B-track)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.experimental.btrack_theory_to_gp_orchestrator_v0.equity_gp_resolve_lib_v1 import (
    REGISTRY,
    apply_resolves,
    eval_any_close_at_or_above,
    eval_any_close_below,
    eval_daily_drop,
    load_equity_csv,
    parse_utc,
    utc_now,
)

DEFAULT_OUT = ROOT / "reports" / "general_prophecy_logos_june_resolve_eval_v1_latest.json"

JUNE_START = "2026-06-01"
JUNE_END = "2026-06-30"
BRENT_START = "2026-06-04"

KOSPI_QID = "gp_2026_logos_kospi_close_below_8500_by_0630"
NASDAQ_QID = "gp_2026_logos_nasdaq_daily_drop_ge_3pct_june"
BRENT_QID = "gp_2026_logos_brent_spot_ge_95_before_0701"
VIX_QID = "gp_2026_logos_vix_close_ge_25_june"

CSV_PATHS = {
    KOSPI_QID: ROOT / "research/market_data/kospi_daily_external_yf.csv",
    NASDAQ_QID: ROOT / "research/market_data/nasdaq_daily_external_yf.csv",
    BRENT_QID: ROOT / "research/market_data/brent_daily_external.csv",
    VIX_QID: ROOT / "research/market_data/vix_daily_external_yf.csv",
}

DEADLINES = {
    KOSPI_QID: "2026-06-30T06:30:00Z",
    NASDAQ_QID: "2026-07-01T04:00:00Z",
    BRENT_QID: "2026-07-01T05:00:00Z",
    VIX_QID: "2026-07-01T04:00:00Z",
}


def _eval_kospi(df) -> dict[str, Any]:
    return eval_any_close_below(df, JUNE_START, JUNE_END, 8500.0)


def _eval_nasdaq(df) -> dict[str, Any]:
    return eval_daily_drop(df, JUNE_START, JUNE_END, 0.03)


def _eval_brent(df) -> dict[str, Any]:
    return eval_any_close_at_or_above(df, BRENT_START, JUNE_END, 95.0)


def _eval_vix(df) -> dict[str, Any]:
    return eval_any_close_at_or_above(df, JUNE_START, JUNE_END, 25.0)


EVAL_FNS = {
    KOSPI_QID: _eval_kospi,
    NASDAQ_QID: _eval_nasdaq,
    BRENT_QID: _eval_brent,
    VIX_QID: _eval_vix,
}


def evaluate_all() -> dict[str, Any]:
    evaluations: dict[str, dict[str, Any]] = {}
    csv_meta: dict[str, Any] = {}
    ok = True
    for qid, csv_path in CSV_PATHS.items():
        if not csv_path.is_file():
            evaluations[qid] = {"ok": False, "error": "csv_missing", "outcome_binary": None}
            ok = False
            continue
        df = load_equity_csv(csv_path)
        csv_meta[qid] = {"path": str(csv_path.relative_to(ROOT)).replace("\\", "/"), "last_date": str(df["Date"].iloc[-1])}
        ev = EVAL_FNS[qid](df)
        ev["deadline_utc"] = DEADLINES[qid]
        ev["deadline_passed"] = datetime.now(timezone.utc) >= parse_utc(DEADLINES[qid])
        evaluations[qid] = ev
        if not ev.get("ok"):
            ok = False
    return {"ok": ok, "csv_meta": csv_meta, "evaluations": evaluations}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force-apply", action="store_true")
    ap.add_argument("--run-brier", action="store_true")
    ns = ap.parse_args()

    now = datetime.now(timezone.utc)
    body = evaluate_all()
    body.update(
        {
            "schema": "general_prophecy_logos_june_resolve_eval_v1",
            "generated_at_utc": utc_now(),
            "hypothesis_tier": "B",
            "research_only": True,
            "apply_requested": ns.apply or ns.force_apply,
            "partial_june_note": "Preview before month-end; outcomes may change as CSV rows accumulate.",
        }
    )

    if (ns.apply or ns.force_apply) and body.get("ok"):
        to_apply: dict[str, dict[str, Any]] = {}
        blocked: list[str] = []
        for qid, ev in (body.get("evaluations") or {}).items():
            dl = parse_utc(DEADLINES[qid])
            if now >= dl or ns.force_apply:
                to_apply[qid] = ev
            else:
                blocked.append(qid)
        if blocked:
            body["apply_blocked_qids"] = blocked
        if to_apply:
            body["apply_results"] = apply_resolves(
                ns.registry,
                to_apply,
                notes_prefix=f"partial_june_preview={body.get('generated_at_utc')}",
                notes_tag="auto_logos_june_resolve_v1",
            )
        if ns.run_brier and to_apply:
            cp = __import__("subprocess").run(
                [sys.executable, str(ROOT / "scripts/eval_general_prophecy_brier_score.py")],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            body["brier_exit_code"] = cp.returncode

    ns.out_json.parent.mkdir(parents=True, exist_ok=True)
    ns.out_json.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": body.get("ok"), "out": str(ns.out_json)}, ensure_ascii=False))
    return 0 if body.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
