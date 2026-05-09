#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Reselect locked sigma from latest h2h report.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument(
        "--h2h-report-json",
        type=Path,
        default=root / "reports" / "agct_sigma_head_to_head_3batch_v1_latest.json",
    )
    ap.add_argument(
        "--policy-json",
        type=Path,
        default=root / "docs" / "final" / "artifacts" / "agct_sigma_lock_policy_v1.json",
    )
    ap.add_argument("--go-rate-floor", type=float, default=0.25)
    ap.add_argument("--transition-floor", type=float, default=0.45)
    ns = ap.parse_args()

    h2h = _read_json(ns.h2h_report_json)
    rows = h2h.get("rows", [])
    if not rows:
        raise SystemExit("No rows in h2h report.")

    ranked = sorted(
        rows,
        key=lambda r: (
            -float(r.get("go_rate_mean", 0.0)),
            -float(r.get("transition_intensity_mean", 0.0)),
            float(r.get("go_rate_std", 1.0)),
        ),
    )
    top = ranked[0]
    candidate = float(top["sigma"])
    go_ok = float(top.get("go_rate_mean", 0.0)) >= ns.go_rate_floor
    ti_ok = float(top.get("transition_intensity_mean", 0.0)) >= ns.transition_floor
    status = "accepted" if (go_ok and ti_ok) else "warning"

    payload = {
        "schema": "agct_sigma_lock_policy_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "locked_sigma": candidate,
        "source": "auto_reselection_from_h2h",
        "selection_status": status,
        "selection_metrics": {
            "go_rate_mean": top.get("go_rate_mean"),
            "go_rate_std": top.get("go_rate_std"),
            "transition_intensity_mean": top.get("transition_intensity_mean"),
            "transition_intensity_std": top.get("transition_intensity_std"),
            "go_rate_floor": ns.go_rate_floor,
            "transition_floor": ns.transition_floor,
            "go_floor_ok": go_ok,
            "transition_floor_ok": ti_ok,
        },
        "h2h_report": str(ns.h2h_report_json.resolve()),
        "notes": [
            "Policy update is B-track only.",
            "If selection_status=warning, keep human review gate before long-run lock."
        ],
    }
    ns.policy_json.parent.mkdir(parents=True, exist_ok=True)
    ns.policy_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.policy_json.resolve()} locked_sigma={candidate} status={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
