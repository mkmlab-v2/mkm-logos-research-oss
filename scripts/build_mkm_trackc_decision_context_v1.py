#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _safe_get(d: dict, *keys: str):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Track C decision context artifact.")
    ap.add_argument("--dashboard-json", default="docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json")
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/mkm_trackc_decision_context_latest.json",
    )
    ap.add_argument("--recheck-eta", default="P7D")
    args = ap.parse_args()

    p_dash = resolve(args.dashboard_json)
    out_path = resolve(args.output_json)
    if not p_dash.is_file():
        raise SystemExit(f"missing dashboard json: {p_dash}")

    dashboard = json.loads(p_dash.read_text(encoding="utf-8-sig"))
    decision_state = _safe_get(dashboard, "trackc", "api_decision_state") or "UNKNOWN"
    guard_passed = bool(_safe_get(dashboard, "trackc", "guard_passed"))
    packet_status = str(_safe_get(dashboard, "trackc", "packet_status") or "UNKNOWN")
    pass_rate = _safe_get(dashboard, "system", "weekly_pass_rate_percent")
    sample_count = _safe_get(dashboard, "system", "weekly_sample_count")

    if decision_state == "WATCH" and guard_passed and packet_status == "READY":
        decision_reason = "Conservative policy state: WATCH remains active with guard while readiness stays healthy."
        next_trigger = "Promote from WATCH only when WATCH-exit KPI contract is fully satisfied."
    elif decision_state == "GO":
        decision_reason = "Track C currently in GO state."
        next_trigger = "Continue monitoring and enforce guard integrity."
    else:
        decision_reason = "Decision state requires manual review due to unknown or non-standard state."
        next_trigger = "Run governance review and update decision mapping."

    payload = {
        "schema": "mkm_trackc_decision_context_v1",
        "generated_at_utc": utc_now(),
        "input_dashboard": str(p_dash),
        "decision_context": {
            "decision_state": decision_state,
            "decision_reason": decision_reason,
            "next_trigger": next_trigger,
            "recheck_eta": args.recheck_eta,
        },
        "observed_snapshot": {
            "guard_passed": guard_passed,
            "packet_status": packet_status,
            "weekly_pass_rate_percent": pass_rate,
            "weekly_sample_count": sample_count,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
