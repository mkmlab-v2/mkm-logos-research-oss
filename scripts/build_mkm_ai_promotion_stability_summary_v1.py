#!/usr/bin/env python3
"""Single-file promotion + edge M1 stability gate (post daily readiness)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/mkm_ai_promotion_stability_summary_latest.json"

PATHS = {
    "pointer": ROOT / "docs/final/artifacts/mkm_ai_status_pointer_latest.json",
    "lock": ROOT / "docs/final/artifacts/mkm_ai_v2_final_promotion_lock_latest.json",
    "decision": ROOT / "docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json",
    "weekly": ROOT / "docs/final/artifacts/mkm_ai_v2_weekly_readiness_report_latest.json",
    "readiness": ROOT / "docs/final/artifacts/mkm_ai_v2_readiness_latest.json",
    "edge": ROOT / "reports/edge_m1_relay_chain_status_latest.json",
    "encoding": ROOT / "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json",
    "exclusions_audit": ROOT / "docs/final/artifacts/mkm_ai_v2_weekly_exclusions_audit_v1_latest.json",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def build() -> dict[str, Any]:
    pointer = _read(PATHS["pointer"])
    weekly = _read(PATHS["weekly"])
    readiness = _read(PATHS["readiness"])
    edge = _read(PATHS["edge"])
    encoding = _read(PATHS["encoding"])

    checks: list[dict[str, Any]] = []
    ok_flags: list[bool] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})
        ok_flags.append(passed)

    approved = pointer and pointer.get("status") == "APPROVED_FINAL_V2"
    add("mkm_ai_status_pointer", approved, f"status={pointer.get('status') if pointer else 'missing'}")

    weekly_ok = bool(weekly and float(weekly.get("pass_rate_percent", 0)) >= 95.0)
    add(
        "weekly_pass_rate",
        weekly_ok,
        f"pass_rate={weekly.get('pass_rate_percent') if weekly else 'missing'} "
        f"sample={weekly.get('sample_count') if weekly else '?'}",
    )

    readiness_ok = bool(readiness and readiness.get("overall_passed"))
    add("readiness_overall", readiness_ok, f"overall_passed={readiness.get('overall_passed') if readiness else 'missing'}")

    core_ok = bool(encoding and encoding.get("rq_019_milestones_core_ready"))
    add("rq_019_core_ready", core_ok, f"core_ready={encoding.get('rq_019_milestones_core_ready') if encoding else 'missing'}")

    edge_ok = bool(edge and edge.get("combined_pass"))
    add("edge_m1_combined_pass", edge_ok, f"combined_pass={edge.get('combined_pass') if edge else 'missing'}")

    stable = all(ok_flags) if ok_flags else False
    watch: list[str] = []
    if not approved:
        watch.append("mkm_ai_status_not_approved_final_v2")
    if not weekly_ok:
        watch.append("weekly_pass_rate_below_95")
    if not readiness_ok:
        watch.append("readiness_overall_failed")
    if not core_ok:
        watch.append("rq_019_core_not_ready")
    if not edge_ok:
        watch.append("edge_m1_combined_pass_false")

    return {
        "schema": "mkm_ai_promotion_stability_summary_v1",
        "generated_at_utc": _utc(),
        "stable": stable,
        "final_action_hint": "STABLE" if stable else "WATCH",
        "watch_reasons": watch,
        "checks": checks,
        "artifacts": {k: str(v) for k, v in PATHS.items()},
        "snapshot": {
            "pointer_status": pointer.get("status") if pointer else None,
            "weekly_pass_rate_percent": weekly.get("pass_rate_percent") if weekly else None,
            "edge_combined_pass": edge.get("combined_pass") if edge else None,
            "rq_019_core_ready": encoding.get("rq_019_milestones_core_ready") if encoding else None,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict-exit", action="store_true", help="Exit 1 when not stable")
    args = ap.parse_args()
    doc = build()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "stable": doc["stable"], "out": str(out)}, ensure_ascii=False))
    if args.strict_exit and not doc["stable"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
