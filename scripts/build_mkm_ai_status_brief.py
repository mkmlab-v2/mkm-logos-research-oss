from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build human-readable MKM AI status brief.")
    parser.add_argument("--workspace-root", default="C:/workspace")
    return parser.parse_args()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def main() -> int:
    args = _parse_args()
    root = Path(args.workspace_root)

    pointer_path = root / "docs" / "final" / "artifacts" / "mkm_ai_status_pointer_latest.json"
    weekly_path = root / "docs" / "final" / "artifacts" / "mkm_ai_v2_weekly_readiness_report_latest.json"
    decision_path = root / "docs" / "final" / "artifacts" / "mkm_ai_v2_promotion_decision_latest.json"
    trackc_dashboard_path = root / "docs" / "final" / "artifacts" / "mkm_trackc_ops_dashboard_latest.json"
    watch_alert_path = root / "docs" / "final" / "artifacts" / "mkm_trackc_watch_prolonged_alert_latest.json"
    ab_gate_path = root / "docs" / "final" / "artifacts" / "mkm_atrack_btrack_contamination_gate_latest.json"
    out_path = root / "docs" / "final" / "artifacts" / "mkm_ai_status_brief_latest.md"

    pointer = _read_json(pointer_path)
    weekly = _read_json(weekly_path)
    decision = _read_json(decision_path)
    trackc_dashboard = _read_json(trackc_dashboard_path)
    watch_alert = _read_json(watch_alert_path)
    ab_gate = _read_json(ab_gate_path)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    status = pointer.get("status", "UNKNOWN")
    label = pointer.get("system_label", "Unknown")
    is_final = bool(pointer.get("is_final", False))
    pass_rate = weekly.get("pass_rate_percent")
    sample_count = weekly.get("sample_count")
    promo_decision = decision.get("decision")
    reasons = decision.get("reasons", [])
    reason_text = "; ".join(str(r) for r in reasons) if reasons else "n/a"
    trackc_state = ((trackc_dashboard.get("trackc") or {}).get("api_decision_state")) or "UNKNOWN"
    watch_status = watch_alert.get("status", "UNKNOWN")
    watch_streak_days = watch_alert.get("watch_streak_days", "UNKNOWN")
    watch_threshold_days = watch_alert.get("threshold_days", "UNKNOWN")
    ab_gate_status = ab_gate.get("status", "UNKNOWN")

    residual_risks = []
    if trackc_state == "WATCH":
        residual_risks.append("Track C remains in WATCH; expansion is constrained by conservative guard policy.")
    if watch_status != "OK":
        residual_risks.append("Prolonged WATCH alert is not OK; immediate human review required.")
    if ab_gate_status != "PASS_CLEAN":
        residual_risks.append("A/B contamination gate is not clean; A-track decision integrity may be at risk.")
    if not residual_risks:
        residual_risks.append("No critical residual risk flags detected from current guard artifacts.")

    no_go_clauses = [
        "Do not auto-bridge B-track outputs into A-track decision inputs.",
        "Do not promote external claims to FACT without artifact-backed verification.",
        "Do not expand Track C while WATCH exit KPI contract is unsatisfied.",
    ]
    recheck_triggers = [
        f"Immediate recheck if watch alert status changes from OK (current: {watch_status}).",
        f"Immediate recheck if A/B contamination gate deviates from PASS_CLEAN (current: {ab_gate_status}).",
        f"Scheduled recheck while WATCH streak progresses ({watch_streak_days}/{watch_threshold_days} days).",
    ]

    lines = [
        "# MKM AI Status Brief (Latest)",
        "",
        f"- generated_at_utc: `{now}`",
        f"- status: `{status}`",
        f"- system_label: `{label}`",
        f"- is_final: `{str(is_final).lower()}`",
        f"- promotion_decision: `{promo_decision}`",
        f"- weekly_pass_rate_percent: `{pass_rate}`",
        f"- weekly_sample_count: `{sample_count}`",
        f"- decision_reasons: `{reason_text}`",
        "",
        "## Evidence",
        f"- `docs/final/artifacts/{pointer_path.name}`",
        f"- `docs/final/artifacts/{weekly_path.name}`",
        f"- `docs/final/artifacts/{decision_path.name}`",
        f"- `docs/final/artifacts/{trackc_dashboard_path.name}`",
        f"- `docs/final/artifacts/{watch_alert_path.name}`",
        f"- `docs/final/artifacts/{ab_gate_path.name}`",
        "",
        "## Residual Risk",
        *[f"- {item}" for item in residual_risks],
        "",
        "## No-Go Clauses",
        *[f"- {item}" for item in no_go_clauses],
        "",
        "## Recheck Triggers",
        *[f"- {item}" for item in recheck_triggers],
    ]

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"status brief written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
