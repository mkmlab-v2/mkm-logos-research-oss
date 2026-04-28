#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "pointerguard_ops_alert_delivery_latest.json"

SMOKE_DEFAULT = ART / "pointerguard_operational_smoke_latest.json"
GUARD_DEFAULT = ART / "genesis_pointer_routing_decision_guarded_latest.json"
READINESS_DEFAULT = ART / "pointerguard_ops_readiness_latest.json"
SECURITY_DEFAULT = ART / "pointerguard_security_hardening_latest.json"
FAILURE_TOPN_DEFAULT = ART / "pointerguard_readiness_failure_topn_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _should_alert(
    smoke: dict[str, Any],
    guard: dict[str, Any],
    readiness: dict[str, Any],
    security: dict[str, Any],
    always: bool,
) -> tuple[bool, list[str], str]:
    reasons: list[str] = []
    severity = "INFO"
    if always:
        reasons.append("always_mode")
    if not bool(smoke.get("all_ok", False)):
        reasons.append("operational_smoke_failed")
        severity = "P0"
    if bool(guard.get("guard_applied", False)):
        reasons.append("guard_downgrade_applied")
        severity = "P0"
    if not bool(readiness.get("all_ok", False)):
        reasons.append("ops_readiness_failed")
        severity = "P0"
    if not bool(security.get("all_ok", False)):
        reasons.append("hardening_all_ok_false")
        severity = "P0"

    # Promote specific readiness/security failures to P0.
    checks = readiness.get("checks", []) if isinstance(readiness, dict) else []
    for c in checks:
        reason = str(c.get("reason", ""))
        if reason in {"launch_checklist_not_ready", "manual_promotion_lock_disabled", "two_person_review_disabled", "approval_log_required_disabled"}:
            reasons.append(reason)
            severity = "P0"
    controls = security.get("controls", {}) if isinstance(security, dict) else {}
    if str(controls.get("leaked_info_scanner", {}).get("status")) == "FAIL":
        reasons.append("unauthorized_pattern_detected")
        severity = "P0"

    # dedupe while preserving order
    deduped: list[str] = []
    for r in reasons:
        if r not in deduped:
            deduped.append(r)
    return (len(deduped) > 0), deduped, severity


def _post_json(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url=url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = getattr(resp, "status", 200)
            return (200 <= int(code) < 300), f"http_{code}"
    except Exception as exc:
        return False, f"error:{exc}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke-json", type=Path, default=SMOKE_DEFAULT)
    ap.add_argument("--guard-json", type=Path, default=GUARD_DEFAULT)
    ap.add_argument("--readiness-json", type=Path, default=READINESS_DEFAULT)
    ap.add_argument("--security-json", type=Path, default=SECURITY_DEFAULT)
    ap.add_argument("--failure-topn-json", type=Path, default=FAILURE_TOPN_DEFAULT)
    ap.add_argument("--always", action="store_true")
    ap.add_argument(
        "--simulate",
        type=str,
        default="",
        help="Comma-separated simulated reasons (e.g. guard_applied,unauthorized_pattern_detected,launch_checklist_not_ready).",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    smoke_path = args.smoke_json if args.smoke_json.is_absolute() else ROOT / args.smoke_json
    guard_path = args.guard_json if args.guard_json.is_absolute() else ROOT / args.guard_json
    readiness_path = args.readiness_json if args.readiness_json.is_absolute() else ROOT / args.readiness_json
    security_path = args.security_json if args.security_json.is_absolute() else ROOT / args.security_json
    failure_topn_path = args.failure_topn_json if args.failure_topn_json.is_absolute() else ROOT / args.failure_topn_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    smoke = _read_json(smoke_path)
    guard = _read_json(guard_path)
    readiness = _read_json(readiness_path) if readiness_path.exists() else {"all_ok": False, "checks": [{"reason": "readiness_missing"}]}
    security = _read_json(security_path) if security_path.exists() else {"all_ok": False}
    failure_topn = _read_json(failure_topn_path) if failure_topn_path.exists() else {}
    should_send, reasons, severity = _should_alert(smoke, guard, readiness, security, bool(args.always))
    sim = [s.strip() for s in str(args.simulate).split(",") if s.strip()]
    if sim:
        should_send = True
        severity = "P0"
        reasons = sim
    webhook = os.getenv("POINTERGUARD_OPS_WEBHOOK_URL", "").strip() or os.getenv("OPS_ALARM_WEBHOOK_URL", "").strip()

    payload = {
        "source": "pointerguard_ops_alert_v1",
        "generated_at_utc": _now_utc(),
        "should_send": should_send,
        "severity": severity,
        "reasons": reasons,
        "smoke_all_ok": bool(smoke.get("all_ok", False)),
        "guard_applied": bool(guard.get("guard_applied", False)),
        "guard_reason": guard.get("guard_reason"),
        "readiness_all_ok": bool(readiness.get("all_ok", False)),
        "security_all_ok": bool(security.get("all_ok", False)),
        "top_repair_priority": (failure_topn.get("repair_queue_topn") or [None])[0],
    }

    sent = False
    delivery_status = "skipped_no_alert"
    if should_send:
        if args.dry_run:
            delivery_status = "dry_run"
        elif not webhook:
            delivery_status = "missing_webhook_env"
        else:
            sent, delivery_status = _post_json(webhook, payload)

    out_doc = {
        "schema": "pointerguard_ops_alert_delivery_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "smoke_json": str(smoke_path),
            "guard_json": str(guard_path),
            "readiness_json": str(readiness_path),
            "security_json": str(security_path),
            "failure_topn_json": str(failure_topn_path),
            "always": bool(args.always),
            "simulate": sim,
            "dry_run": bool(args.dry_run),
        },
        "alert": payload,
        "delivery": {
            "webhook_configured": bool(webhook),
            "sent": sent,
            "status": delivery_status,
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "status": delivery_status, "should_send": should_send}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
