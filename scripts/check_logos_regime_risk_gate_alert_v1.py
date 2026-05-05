#!/usr/bin/env python3
"""Check Logos regime/risk-gate state and emit alert summary."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "docs" / "final" / "artifacts" / "logos_regime_risk_gate_state_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_regime_risk_gate_alert_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-triggered-rules", type=int, default=2)
    ap.add_argument("--always-alert-on-force-hold", action="store_true", default=True)
    args = ap.parse_args()

    state = _read_json(args.state_json)
    rows = state.get("rows") if isinstance(state.get("rows"), list) else []
    triggered_rows = [r for r in rows if isinstance(r, dict) and bool(r.get("triggered"))]
    action = str(state.get("effective_action") or "NO_CHANGE")
    lock_state = bool(((state.get("lock_state") or {}).get("price_output_locked")) if isinstance(state.get("lock_state"), dict) else False)

    reasons: list[str] = []
    if len(triggered_rows) >= args.min_triggered_rules:
        reasons.append("multi_rule_trigger")
    if action == "FORCE_HOLD" and args.always_alert_on_force_hold:
        reasons.append("force_hold_action")
    if lock_state:
        reasons.append("price_output_locked")

    should_alert = len(reasons) > 0
    severity = "none"
    if "force_hold_action" in reasons and "multi_rule_trigger" in reasons:
        severity = "high"
    elif should_alert:
        severity = "medium"

    out = {
        "schema": "logos_regime_risk_gate_alert_v1",
        "generated_at_utc": _iso_now(),
        "state_ref": str(args.state_json),
        "inputs": {
            "min_triggered_rules": args.min_triggered_rules,
            "always_alert_on_force_hold": args.always_alert_on_force_hold,
        },
        "snapshot": {
            "effective_action": action,
            "triggered_rule_count": len(triggered_rows),
            "price_output_locked": lock_state,
            "triggered_insight_ids": [str(r.get("insight_id") or "") for r in triggered_rows],
        },
        "should_alert": should_alert,
        "severity": severity,
        "reasons": reasons,
        "operator_note": (
            "No directional execution while lock_state=true."
            if lock_state
            else "Alert driven by multi-rule or force-hold conditions."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), "should_alert": should_alert, "severity": severity}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

