#!/usr/bin/env python3
"""Evaluate + optional apply resolve for Logos SOX general_prophecy questions (B-track).

Preview anytime from CSV; --apply only when deadline UTC has passed (unless --force-apply).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"
SOX_CSV = ROOT / "research" / "market_data" / "sox_daily_external_yf.csv"
RESOLVE = ROOT / "scripts" / "resolve_general_prophecy_question_v1.py"
DEFAULT_OUT = ROOT / "reports" / "general_prophecy_sox_resolve_eval_v1_latest.json"

REFERENCE_DATE = "2026-06-03"
WINDOW_START = "2026-06-04"
WINDOW_END = "2026-09-30"
DROP_WINDOW_START = "2026-07-01"
DROP_WINDOW_END = "2026-09-30"
DEADLINE_UTC = "2026-10-01T00:00:00Z"
DRAWDOWN_MULT = 0.90
DROP_PCT = 0.05

SOX_QIDS = (
    "gp_2026_logos_sox_new_high_before_0930",
    "gp_2026_logos_sox_daily_drop_ge_5pct_q3",
    "gp_2026_logos_sox_close_below_ref_minus_10pct_by_0930",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def _load_sox(csv_path: Path):
    import pandas as pd

    df = pd.read_csv(csv_path)
    df["Date"] = df["Date"].astype(str).str.slice(0, 10)
    df["Close"] = df["Close"].astype(float)
    return df.sort_values("Date").reset_index(drop=True)


def _reference_high(df, reference_date: str) -> float | None:
    ref = df[df["Date"] <= reference_date]
    if ref.empty:
        return None
    return float(ref["Close"].max())


def _slice_window(df, start: str, end: str):
    return df[(df["Date"] >= start) & (df["Date"] <= end)].copy()


def eval_sox_new_high(df, reference_date: str, window_start: str, window_end: str) -> dict[str, Any]:
    rh = _reference_high(df, reference_date)
    if rh is None:
        return {"ok": False, "error": "reference_high_undefined", "outcome_binary": None}
    win = _slice_window(df, window_start, window_end)
    if win.empty:
        return {"ok": True, "reference_high": rh, "outcome_binary": False, "hit_dates": []}
    hits = win[win["Close"] > rh]
    ob = len(hits) > 0
    return {
        "ok": True,
        "reference_high": rh,
        "outcome_binary": ob,
        "hit_dates": hits["Date"].tolist()[:5],
        "window_rows": int(len(win)),
    }


def eval_sox_daily_drop(df, drop_start: str, drop_end: str, drop_pct: float) -> dict[str, Any]:
    win = _slice_window(df, drop_start, drop_end)
    if len(win) < 2:
        return {"ok": True, "outcome_binary": False, "hit_dates": [], "window_rows": int(len(win))}
    win = win.sort_values("Date").reset_index(drop=True)
    ret = win["Close"].pct_change()
    hits = win[ret <= -drop_pct]
    return {
        "ok": True,
        "outcome_binary": len(hits) > 0,
        "hit_dates": hits["Date"].tolist()[:5],
        "window_rows": int(len(win)),
    }


def eval_sox_drawdown(df, reference_date: str, window_start: str, window_end: str, mult: float) -> dict[str, Any]:
    rh = _reference_high(df, reference_date)
    if rh is None:
        return {"ok": False, "error": "reference_high_undefined", "outcome_binary": None}
    threshold = rh * mult
    win = _slice_window(df, window_start, window_end)
    hits = win[win["Close"] <= threshold] if not win.empty else win
    return {
        "ok": True,
        "reference_high": rh,
        "threshold": threshold,
        "outcome_binary": len(hits) > 0,
        "hit_dates": hits["Date"].tolist()[:5] if len(hits) else [],
        "window_rows": int(len(win)),
    }


def evaluate_all(csv_path: Path) -> dict[str, Any]:
    if not csv_path.is_file():
        return {"ok": False, "error": "csv_missing", "evaluations": {}}
    df = _load_sox(csv_path)
    last_date = str(df["Date"].iloc[-1]) if len(df) else None
    ev = {
        SOX_QIDS[0]: eval_sox_new_high(df, REFERENCE_DATE, WINDOW_START, WINDOW_END),
        SOX_QIDS[1]: eval_sox_daily_drop(df, DROP_WINDOW_START, DROP_WINDOW_END, DROP_PCT),
        SOX_QIDS[2]: eval_sox_drawdown(df, REFERENCE_DATE, WINDOW_START, WINDOW_END, DRAWDOWN_MULT),
    }
    return {"ok": True, "csv_last_date": last_date, "evaluations": ev}


def apply_resolves(registry: Path, evaluations: dict[str, dict[str, Any]], *, notes_prefix: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for qid, ev in evaluations.items():
        if not ev.get("ok") or ev.get("outcome_binary") is None:
            results.append({"question_id": qid, "applied": False, "reason": ev.get("error", "eval_failed")})
            continue
        outcome = "true" if ev["outcome_binary"] else "false"
        cmd = [
            sys.executable,
            str(RESOLVE),
            "-i",
            str(registry),
            "--in-place",
            "--question-id",
            qid,
            "--resolution-status",
            "resolved",
            "--outcome",
            outcome,
            "--notes",
            f"{notes_prefix}; auto_sox_resolve_v1",
        ]
        cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        results.append(
            {
                "question_id": qid,
                "applied": cp.returncode == 0,
                "outcome": outcome,
                "exit_code": cp.returncode,
                "stderr_tail": (cp.stderr or "")[-300:],
            }
        )
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=SOX_CSV)
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--apply", action="store_true", help="Write resolve to registry when deadline passed")
    ap.add_argument("--force-apply", action="store_true", help="Apply even before deadline (research only)")
    ap.add_argument("--run-brier", action="store_true", help="After apply, run eval_general_prophecy_brier_score.py")
    ns = ap.parse_args()

    now = datetime.now(timezone.utc)
    deadline = _parse_utc(DEADLINE_UTC)
    deadline_passed = now >= deadline

    body = evaluate_all(ns.csv)
    body.update(
        {
            "schema": "general_prophecy_sox_resolve_eval_v1",
            "generated_at_utc": _utc_now(),
            "hypothesis_tier": "B",
            "research_only": True,
            "deadline_utc": DEADLINE_UTC,
            "deadline_passed": deadline_passed,
            "apply_requested": ns.apply or ns.force_apply,
        }
    )

    if (ns.apply or ns.force_apply) and body.get("ok"):
        if not deadline_passed and not ns.force_apply:
            body["apply_blocked"] = "deadline_not_passed"
        else:
            body["apply_results"] = apply_resolves(
                ns.registry,
                body.get("evaluations") or {},
                notes_prefix=f"csv_last={body.get('csv_last_date')}",
            )
            if ns.run_brier:
                cp = subprocess.run(
                    [sys.executable, str(ROOT / "scripts/eval_general_prophecy_brier_score.py")],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                body["brier_exit_code"] = cp.returncode
                body["brier_stdout"] = (cp.stdout or "").strip()[-500:]

    ns.out_json.parent.mkdir(parents=True, exist_ok=True)
    ns.out_json.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = body.get("ok", False)
    print(json.dumps({"ok": ok, "deadline_passed": deadline_passed, "out": str(ns.out_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
