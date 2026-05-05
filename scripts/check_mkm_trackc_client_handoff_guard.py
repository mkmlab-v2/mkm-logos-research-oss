from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


STATUS_APPROVED_FINAL_V2 = "APPROVED_FINAL_V2"
STATUS_HOLD_OPERATIONAL_V1 = "HOLD_OPERATIONAL_V1"


def _check(doc: Dict[str, Any], *, strict_final: bool) -> tuple[List[str], str]:
    """Returns (failure_codes, approval_tier: final | operational_hold | none)."""
    failures: List[str] = []

    if doc.get("schema") != "mkm_trackc_client_handoff_package_v1":
        failures.append("schema_mismatch")

    if doc.get("packet_status") != "READY":
        failures.append("packet_status_not_ready")

    summary = doc.get("executive_summary", {})
    status = summary.get("status")
    approval_tier = "none"
    checklist = doc.get("delivery_checklist", {})

    required_true = [
        "commercial_package_ready",
        "external_onepager_ready",
        "api_spec_package_ready",
        "macro_risk_api_smoke_present",
        "macro_risk_policy_present",
        "showroom_readiness_present",
    ]
    for key in required_true:
        if checklist.get(key) is not True:
            failures.append(f"checklist_not_true:{key}")

    checklist_ok = not any(x.startswith("checklist_not_true:") for x in failures)

    if status == STATUS_APPROVED_FINAL_V2:
        approval_tier = "final"
    elif (
        not strict_final
        and status == STATUS_HOLD_OPERATIONAL_V1
        and doc.get("packet_status") == "READY"
        and checklist_ok
    ):
        approval_tier = "operational_hold"
    else:
        failures.append("system_status_not_approved_final_v2")

    return failures, approval_tier


def main() -> int:
    p = argparse.ArgumentParser(description="Hard guard for MKM Track C client handoff package.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument(
        "--handoff-json",
        default="docs/final/artifacts/mkm_trackc_client_handoff_package_latest.json",
    )
    p.add_argument(
        "--strict-final",
        action="store_true",
        help="Require executive_summary.status APPROVED_FINAL_V2 (reject HOLD_OPERATIONAL_V1).",
    )
    args = p.parse_args()

    root = Path(args.workspace_root).resolve()
    handoff_path = (root / args.handoff_json).resolve()
    if not handoff_path.exists():
        print(f"TRACKC HANDOFF GUARD: FAIL missing file: {handoff_path}")
        return 1

    try:
        doc = _read_json(handoff_path)
    except Exception as exc:
        print(f"TRACKC HANDOFF GUARD: FAIL json parse error: {type(exc).__name__}")
        return 1

    failures, approval_tier = _check(doc, strict_final=args.strict_final)
    report = {
        "schema": "mkm_trackc_client_handoff_guard_report_v1",
        "generated_at_utc": _utc_now(),
        "handoff_path": str(handoff_path).replace("\\", "/"),
        "passed": len(failures) == 0,
        "failures": failures,
        "approval_tier": approval_tier,
        "strict_final": bool(args.strict_final),
        "packet_status": doc.get("packet_status"),
        "system_status": (doc.get("executive_summary", {}) or {}).get("status"),
    }

    out = root / "docs/final/artifacts/mkm_trackc_client_handoff_guard_latest.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if failures:
        print("TRACKC HANDOFF GUARD: FAIL")
        for f in failures:
            print(f"- {f}")
        print(f"report: {out}")
        return 1

    print("TRACKC HANDOFF GUARD: PASS")
    print(f"report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
