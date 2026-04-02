#!/usr/bin/env python3
"""Check current Aegis scoreboard against C2 baseline guardrail."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GUARD = ROOT / "docs" / "final" / "artifacts" / "C2_AEGIS_BASELINE_GUARDRAIL_V1.json"
DEFAULT_CURRENT = ROOT / "docs" / "final" / "artifacts" / "aegis_unified_scoreboard_btc90_k010_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "c2_aegis_guardrail_status_latest.json"
DEFAULT_HISTORY = ROOT / "docs" / "final" / "artifacts" / "c2_aegis_guardrail_history.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip().lstrip("\ufeff")
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare current Aegis score to C2 guardrail baseline.")
    ap.add_argument("--guardrail", type=Path, default=DEFAULT_GUARD)
    ap.add_argument("--current", type=Path, default=DEFAULT_CURRENT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--lookback-days", type=int, default=14)
    ap.add_argument("--yellow-count-threshold", type=int, default=3)
    ap.add_argument("--red-count-threshold", type=int, default=1)
    ap.add_argument("--ace-change-threshold", type=int, default=3)
    args = ap.parse_args()

    guard = _read_json(args.guardrail)
    cur = _read_json(args.current)
    if not guard or not cur:
        raise SystemExit("Missing or invalid guardrail/current JSON")

    base = guard.get("baseline") if isinstance(guard.get("baseline"), dict) else {}
    th = guard.get("thresholds") if isinstance(guard.get("thresholds"), dict) else {}
    ace = cur.get("ace_profile") if isinstance(cur.get("ace_profile"), dict) else {}
    baseline_score = float(base.get("unified_score_balanced") or 0.0)
    baseline_profile = str(base.get("profile") or "")
    current_profile = str(ace.get("profile") or "")
    current_score = float(((ace.get("baseline_7_3") or {}).get("unified_score_balanced") or 0.0))
    delta = current_score - baseline_score

    warn_drop = float(th.get("warn_drop_abs") or 0.005)
    alert_drop = float(th.get("alert_drop_abs") or 0.02)
    recover_gain = float(th.get("recover_gain_abs") or 0.005)

    status = "GREEN_HOLD"
    if delta <= -alert_drop:
        status = "RED_ALERT_DROP"
    elif delta <= -warn_drop:
        status = "YELLOW_WARN_DROP"
    elif delta >= recover_gain:
        status = "BLUE_RECOVERY_GAIN"

    # History-based structural break rule:
    # - RED count >= threshold OR YELLOW count >= threshold OR ace profile changes >= threshold.
    now_utc = datetime.now(timezone.utc)
    history_rows = _read_jsonl(args.history)
    current_event = {
        "generated_at_utc": _utc_now(),
        "status": status,
        "ace_profile": current_profile,
        "delta_vs_baseline": round(delta, 6),
    }
    history_rows.append(current_event)
    args.history.parent.mkdir(parents=True, exist_ok=True)
    with args.history.open("w", encoding="utf-8") as f:
        for row in history_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    lookback = max(1, int(args.lookback_days))
    recent: list[dict[str, Any]] = []
    for row in history_rows:
        ts = str(row.get("generated_at_utc") or "")
        try:
            row_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if (now_utc - row_dt).days <= lookback:
            recent.append(row)

    yellow_count = sum(1 for r in recent if str(r.get("status") or "") == "YELLOW_WARN_DROP")
    red_count = sum(1 for r in recent if str(r.get("status") or "") == "RED_ALERT_DROP")
    ace_changes = 0
    prev = None
    for r in recent:
        cur_ace = str(r.get("ace_profile") or "")
        if prev is not None and cur_ace and cur_ace != prev:
            ace_changes += 1
        if cur_ace:
            prev = cur_ace

    structural_break_alert = (
        (red_count >= max(1, int(args.red_count_threshold)))
        or (yellow_count >= max(1, int(args.yellow_count_threshold)))
        or (ace_changes >= max(1, int(args.ace_change_threshold)))
    )

    structural_break_reasons: list[str] = []
    if red_count >= max(1, int(args.red_count_threshold)):
        structural_break_reasons.append("red_count_threshold_met")
    if yellow_count >= max(1, int(args.yellow_count_threshold)):
        structural_break_reasons.append("yellow_count_threshold_met")
    if ace_changes >= max(1, int(args.ace_change_threshold)):
        structural_break_reasons.append("ace_change_threshold_met")

    payload = {
        "schema": "c2_aegis_guardrail_status_v1",
        "generated_at_utc": _utc_now(),
        "exploratory_only": True,
        "a_track_binding_forbidden": True,
        "inputs": {
            "guardrail": str(args.guardrail.resolve()),
            "current": str(args.current.resolve()),
        },
        "baseline": {
            "profile": baseline_profile,
            "unified_score_balanced": round(baseline_score, 6),
        },
        "current": {
            "profile": current_profile,
            "unified_score_balanced": round(current_score, 6),
        },
        "delta_vs_baseline": round(delta, 6),
        "status": status,
        "thresholds": {
            "warn_drop_abs": warn_drop,
            "alert_drop_abs": alert_drop,
            "recover_gain_abs": recover_gain,
        },
        "structural_break_rule": {
            "lookback_days": lookback,
            "yellow_count_threshold": int(args.yellow_count_threshold),
            "red_count_threshold": int(args.red_count_threshold),
            "ace_change_threshold": int(args.ace_change_threshold),
        },
        "structural_break_window_stats": {
            "window_event_count": len(recent),
            "yellow_count": yellow_count,
            "red_count": red_count,
            "ace_change_count": ace_changes,
        },
        "structural_break_alert": structural_break_alert,
        "structural_break_reasons": structural_break_reasons,
        "note": "C2 comparative guardrail status (monitor-only).",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    print(
        "status={s} delta={d} structural_break_alert={a}".format(
            s=status, d=round(delta, 6), a=str(structural_break_alert).lower()
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

