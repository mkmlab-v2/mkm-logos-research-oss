#!/usr/bin/env python3
"""Dispatch lens music audition governance status to optional webhook (M19).

Advisory-only alert bridge for GO/WATCH status from M17.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATUS = ROOT / "docs" / "final" / "artifacts" / "lens_music_audition_governance_status_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "lens_music_audition_governance_webhook_dispatch_latest.json"


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--status-json", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--webhook-env", type=str, default="LENS_MUSIC_AUDITION_WEBHOOK_URL")
    args = ap.parse_args()

    status_doc = _read_json(args.status_json)
    has_core = bool(status_doc and str(status_doc.get("schema", "")).strip())
    webhook = str(os.environ.get(args.webhook_env, "")).strip()

    payload = {
        "source": "lens_music_audition_governance_webhook_v1",
        "generated_at_utc": _iso_now(),
        "track": "B",
        "advisory_only": True,
        "status": {
            "schema": status_doc.get("schema"),
            "generated_at_utc": status_doc.get("generated_at_utc"),
            "state": status_doc.get("state"),
            "warn_ratio": status_doc.get("warn_ratio"),
            "warn_ratio_threshold": status_doc.get("warn_ratio_threshold"),
            "warn_count": status_doc.get("warn_count"),
            "sample_count": status_doc.get("sample_count"),
        },
        "compliance_note": "Research lane advisory only. No automatic promotion/trading decision.",
        "evidence_ref": str(args.status_json).replace("\\", "/"),
    }

    out: dict[str, Any] = {
        "schema": "lens_music_audition_governance_webhook_dispatch_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "status_json": str(args.status_json).replace("\\", "/"),
            "webhook_env": args.webhook_env,
        },
        "decision": {
            "has_core_inputs": has_core,
            "webhook_configured": bool(webhook),
            "should_dispatch": has_core and bool(webhook),
        },
        "payload_preview": payload,
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
                code = int(resp.getcode())
            out["dispatch"] = {"status": "sent", "http_status": code}
        except (error.URLError, TimeoutError) as exc:
            out["dispatch"] = {"status": "failed", "error": str(exc)}
    elif not has_core:
        out["dispatch"] = {"status": "skipped", "reason": "missing_status_input"}
    else:
        out["dispatch"] = {"status": "skipped", "reason": "webhook_not_configured"}

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "dispatch_status": (out.get("dispatch") or {}).get("status"),
                "output_json": str(args.output_json).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
