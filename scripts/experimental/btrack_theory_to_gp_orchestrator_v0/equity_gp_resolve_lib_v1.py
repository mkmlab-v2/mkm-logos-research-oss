"""Shared CSV evaluation + registry apply for Logos equity general_prophecy (B-track)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"
RESOLVE = ROOT / "scripts" / "resolve_general_prophecy_question_v1.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_equity_csv(csv_path: Path):
    import pandas as pd

    df = pd.read_csv(csv_path)
    df["Date"] = df["Date"].astype(str).str.slice(0, 10)
    df["Close"] = df["Close"].astype(float)
    return df.sort_values("Date").reset_index(drop=True)


def reference_high(df, reference_date: str) -> float | None:
    ref = df[df["Date"] <= reference_date]
    if ref.empty:
        return None
    return float(ref["Close"].max())


def slice_window(df, start: str, end: str):
    return df[(df["Date"] >= start) & (df["Date"] <= end)].copy()


def eval_new_high(
    df,
    reference_date: str,
    window_start: str,
    window_end: str,
) -> dict[str, Any]:
    rh = reference_high(df, reference_date)
    if rh is None:
        return {"ok": False, "error": "reference_high_undefined", "outcome_binary": None}
    win = slice_window(df, window_start, window_end)
    if win.empty:
        return {"ok": True, "reference_high": rh, "outcome_binary": False, "hit_dates": [], "window_rows": 0}
    hits = win[win["Close"] > rh]
    return {
        "ok": True,
        "reference_high": rh,
        "outcome_binary": len(hits) > 0,
        "hit_dates": hits["Date"].tolist()[:5],
        "window_rows": int(len(win)),
    }


def eval_daily_drop(df, drop_start: str, drop_end: str, drop_pct: float) -> dict[str, Any]:
    win = slice_window(df, drop_start, drop_end)
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


def eval_any_close_below(
    df,
    window_start: str,
    window_end: str,
    threshold: float,
) -> dict[str, Any]:
    win = slice_window(df, window_start, window_end)
    if win.empty:
        return {"ok": True, "threshold": threshold, "outcome_binary": False, "hit_dates": [], "window_rows": 0}
    hits = win[win["Close"] < threshold]
    return {
        "ok": True,
        "threshold": threshold,
        "outcome_binary": len(hits) > 0,
        "hit_dates": hits["Date"].tolist()[:5],
        "window_rows": int(len(win)),
    }


def eval_any_close_at_or_above(
    df,
    window_start: str,
    window_end: str,
    threshold: float,
) -> dict[str, Any]:
    win = slice_window(df, window_start, window_end)
    if win.empty:
        return {"ok": True, "threshold": threshold, "outcome_binary": False, "hit_dates": [], "window_rows": 0}
    hits = win[win["Close"] >= threshold]
    return {
        "ok": True,
        "threshold": threshold,
        "outcome_binary": len(hits) > 0,
        "hit_dates": hits["Date"].tolist()[:5],
        "window_rows": int(len(win)),
    }


def eval_drawdown(
    df,
    reference_date: str,
    window_start: str,
    window_end: str,
    mult: float,
) -> dict[str, Any]:
    rh = reference_high(df, reference_date)
    if rh is None:
        return {"ok": False, "error": "reference_high_undefined", "outcome_binary": None}
    threshold = rh * mult
    win = slice_window(df, window_start, window_end)
    hits = win[win["Close"] <= threshold] if not win.empty else win
    return {
        "ok": True,
        "reference_high": rh,
        "threshold": threshold,
        "outcome_binary": len(hits) > 0,
        "hit_dates": hits["Date"].tolist()[:5] if len(hits) else [],
        "window_rows": int(len(win)),
    }


def evaluate_from_csv(
    csv_path: Path,
    *,
    evaluators: dict[str, Any],
) -> dict[str, Any]:
    if not csv_path.is_file():
        return {"ok": False, "error": "csv_missing", "evaluations": {}}
    df = load_equity_csv(csv_path)
    last_date = str(df["Date"].iloc[-1]) if len(df) else None
    evaluations: dict[str, dict[str, Any]] = {}
    for qid, fn in evaluators.items():
        evaluations[qid] = fn(df)
    return {"ok": True, "csv_last_date": last_date, "evaluations": evaluations}


def apply_resolves(
    registry: Path,
    evaluations: dict[str, dict[str, Any]],
    *,
    notes_prefix: str,
    notes_tag: str,
) -> list[dict[str, Any]]:
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
            f"{notes_prefix}; {notes_tag}",
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


def run_resolve_cli(
    *,
    schema: str,
    csv_path: Path,
    registry: Path,
    out_json: Path,
    deadline_utc: str,
    evaluators: dict[str, Any],
    notes_tag: str,
    apply: bool,
    force_apply: bool,
    run_brier: bool,
) -> int:
    now = datetime.now(timezone.utc)
    deadline = parse_utc(deadline_utc)
    deadline_passed = now >= deadline

    body = evaluate_from_csv(csv_path, evaluators=evaluators)
    body.update(
        {
            "schema": schema,
            "generated_at_utc": utc_now(),
            "hypothesis_tier": "B",
            "research_only": True,
            "deadline_utc": deadline_utc,
            "deadline_passed": deadline_passed,
            "apply_requested": apply or force_apply,
        }
    )

    if (apply or force_apply) and body.get("ok"):
        if not deadline_passed and not force_apply:
            body["apply_blocked"] = "deadline_not_passed"
        else:
            body["apply_results"] = apply_resolves(
                registry,
                body.get("evaluations") or {},
                notes_prefix=f"csv_last={body.get('csv_last_date')}",
                notes_tag=notes_tag,
            )
            if run_brier:
                cp = subprocess.run(
                    [sys.executable, str(ROOT / "scripts/eval_general_prophecy_brier_score.py")],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                body["brier_exit_code"] = cp.returncode
                body["brier_stdout"] = (cp.stdout or "").strip()[-500:]

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = body.get("ok", False)
    print(json.dumps({"ok": ok, "deadline_passed": deadline_passed, "out": str(out_json)}, ensure_ascii=False))
    return 0 if ok else 1
