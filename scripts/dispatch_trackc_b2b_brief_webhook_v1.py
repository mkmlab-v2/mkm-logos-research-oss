#!/usr/bin/env python3
"""Dispatch Track C B2B brief payload to webhook (compliance-safe)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_DASHBOARD = ART / "mkm_trackc_ops_dashboard_latest.json"
DEFAULT_ACCEPTANCE = ART / "mkm_trackc_operational_acceptance_latest.json"
DEFAULT_OUTPUT = ART / "trackc_b2b_brief_webhook_dispatch_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _pick(doc: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in keys:
        if k in doc:
            out[k] = doc.get(k)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dashboard-json", type=Path, default=DEFAULT_DASHBOARD)
    ap.add_argument("--acceptance-json", type=Path, default=DEFAULT_ACCEPTANCE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--webhook-env", type=str, default="TRACKC_B2B_BRIEF_WEBHOOK_URL")
    args = ap.parse_args()

    dashboard = _read_json(args.dashboard_json)
    acceptance = _read_json(args.acceptance_json)
    webhook_keys = [args.webhook_env]
    webhook = str(os.environ.get(args.webhook_env, "")).strip()
    webhook_env_used = args.webhook_env
    has_core = bool(dashboard)

    # Compliance-safe fields only (no credentials, no raw internal chain logs).
    system = dashboard.get("system") if isinstance(dashboard.get("system"), dict) else {}
    trackc = dashboard.get("trackc") if isinstance(dashboard.get("trackc"), dict) else {}
    summary = {
        "schema": dashboard.get("schema"),
        "generated_at_utc": dashboard.get("generated_at_utc"),
        "system_status": system.get("status"),
        "promotion_decision": system.get("promotion_decision"),
        "packet_status": trackc.get("packet_status"),
        "guard_passed": trackc.get("guard_passed"),
        "freeze_status": trackc.get("freeze_status"),
    }
    acceptance_summary = {
        "schema": acceptance.get("schema"),
        "generated_at_utc": acceptance.get("generated_at_utc"),
        "acceptance_status": acceptance.get("status") or trackc.get("acceptance_status"),
        "failed_checks": acceptance.get("failed_checks") if isinstance(acceptance.get("failed_checks"), list) else [],
    }

    payload = {
        "source": "trackc_b2b_brief_dispatch_v1",
        "generated_at_utc": _iso_now(),
        "track": "C",
        "scope": "risk_warning_and_exposure_control",
        "compliance_note": "No deterministic prediction claim. No return-assurance claim.",
        "executive_summary": {
            "status": summary.get("system_status", "UNKNOWN"),
            "promotion_decision": summary.get("promotion_decision", "UNKNOWN"),
            "acceptance_status": acceptance_summary.get("acceptance_status", "UNKNOWN"),
        },
        "evidence": {
            "dashboard_ref": str(args.dashboard_json).replace("\\", "/"),
            "acceptance_ref": str(args.acceptance_json).replace("\\", "/"),
        },
        "action": "KEEP_GOVERNED_TRACKC_DISTRIBUTION",
        "risks": acceptance_summary.get("failed_checks") or [],
        "next_checkpoint": "Next daily Track C ops dashboard refresh.",
    }

    out: dict[str, Any] = {
        "schema": "trackc_b2b_brief_webhook_dispatch_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "dashboard_json": str(args.dashboard_json).replace("\\", "/"),
            "acceptance_json": str(args.acceptance_json).replace("\\", "/"),
            "webhook_env": webhook_env_used,
            "webhook_env_candidates": webhook_keys,
        },
        "decision": {
            "has_core_inputs": has_core,
            "webhook_configured": bool(webhook),
            "should_dispatch": has_core and bool(webhook),
        },
        "brief_payload_preview": payload,
    }

    if has_core and webhook:
        req = request.Request(
            webhook,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=10) as resp:
                status_code = int(resp.getcode())
            out["dispatch"] = {"status": "sent", "http_status": status_code}
        except (error.URLError, TimeoutError) as exc:
            out["dispatch"] = {"status": "failed", "error": str(exc)}
    elif not has_core:
        out["dispatch"] = {"status": "skipped", "reason": "missing_core_inputs"}
    else:
        out["dispatch"] = {"status": "skipped", "reason": "webhook_not_configured"}

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "dispatch_status": (out.get("dispatch") or {}).get("status"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

