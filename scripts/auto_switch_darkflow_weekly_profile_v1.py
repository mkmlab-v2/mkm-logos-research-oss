#!/usr/bin/env python3
"""Auto-switch darkflow weekly governance profile based on trend signals."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"
ACTIVE_POLICY = ART / "darkflow_weekly_governance_policy_v1.json"
PRESET_CONSERVATIVE = ART / "darkflow_weekly_governance_policy_preset_conservative_v1.json"
PRESET_AGGRESSIVE = ART / "darkflow_weekly_governance_policy_preset_aggressive_v1.json"
TREND_SUMMARY = ART / "darkflow_ops_trend_summary_latest.json"
DUAL_REPORT = ART / "darkflow_btrack_dual_policy_report_latest.json"
OUT = ART / "darkflow_weekly_profile_autoswitch_latest.json"
LOG = REPORTS / "darkflow_weekly_profile_autoswitch_log.jsonl"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description="Auto-switch darkflow weekly governance profile.")
    ap.add_argument("--apply", action="store_true", help="Apply recommended profile to active policy file.")
    args = ap.parse_args()

    for p in (ACTIVE_POLICY, PRESET_CONSERVATIVE, PRESET_AGGRESSIVE, TREND_SUMMARY, DUAL_REPORT):
        if not p.exists():
            raise FileNotFoundError(f"Missing required file: {p}")

    active = _load(ACTIVE_POLICY)
    trend = _load(TREND_SUMMARY)
    dual = _load(DUAL_REPORT)

    current_profile = str(active.get("profile", "unknown"))
    single_switch = _to_int(trend.get("single_policy_switch_count"))
    top_switch = _to_int(trend.get("top_hypothesis_switch_count"))
    freshness_pass_rate = _to_float(trend.get("freshness_pass_rate"))
    stability_grade = str(trend.get("stability_grade", "UNKNOWN"))
    conservative_decision = str((dual.get("conservative") or {}).get("decision", "n/a"))
    exploratory_decision = str((dual.get("exploratory") or {}).get("decision", "n/a"))

    recommend_profile = current_profile
    reason = "keep_current_profile"

    volatile_signal = (
        stability_grade == "VOLATILE"
        or single_switch >= 3
        or top_switch >= 2
        or freshness_pass_rate < 0.8
    )
    stable_signal = (
        stability_grade == "STABLE"
        and single_switch <= 1
        and top_switch <= 1
        and freshness_pass_rate >= 0.9
    )

    if volatile_signal:
        recommend_profile = "conservative"
        reason = "volatility_or_freshness_risk"
    elif stable_signal and exploratory_decision == "GO_RESEARCH" and conservative_decision != "HOLD_INCONCLUSIVE":
        recommend_profile = "aggressive"
        reason = "stable_with_research_go_signal"

    applied = False
    if args.apply and recommend_profile in ("conservative", "aggressive") and recommend_profile != current_profile:
        src = PRESET_CONSERVATIVE if recommend_profile == "conservative" else PRESET_AGGRESSIVE
        next_policy = _load(src)
        next_policy["profile"] = recommend_profile
        next_policy["activated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        next_policy["auto_switched"] = True
        next_policy["auto_switch_reason"] = reason
        ACTIVE_POLICY.write_text(json.dumps(next_policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        applied = True

    out = {
        "schema": "darkflow_weekly_profile_autoswitch_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "current_profile": current_profile,
        "recommended_profile": recommend_profile,
        "reason": reason,
        "apply_requested": bool(args.apply),
        "applied": applied,
        "signals": {
            "stability_grade": stability_grade,
            "single_policy_switch_count": single_switch,
            "top_hypothesis_switch_count": top_switch,
            "freshness_pass_rate": freshness_pass_rate,
            "dual_conservative_decision": conservative_decision,
            "dual_exploratory_decision": exploratory_decision,
        },
        "evidence_paths": {
            "active_policy": str(ACTIVE_POLICY),
            "trend_summary": str(TREND_SUMMARY),
            "dual_report": str(DUAL_REPORT),
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORTS.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False) + "\n")
    print(str(OUT))
    print(str(LOG))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
