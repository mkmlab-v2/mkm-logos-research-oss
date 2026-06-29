#!/usr/bin/env python3
"""Optional internal hint when A-code promotion_discussion_eligible ([HYPO·non-gating])."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_READINESS = ROOT / "reports/a_code_promotion_checklist_readiness_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/a_code_promotion_discussion_hint_dispatch_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolve_webhook(primary_env: str, fallback_env: str, override: str) -> str:
    if override.strip():
        return override.strip()
    return (os.environ.get(primary_env) or os.environ.get(fallback_env) or "").strip()


def build_dispatch_body(readiness: dict[str, Any]) -> dict[str, Any]:
    summary = readiness.get("summary") or {}
    signoff = readiness.get("signoff") or {}
    return {
        "source": "a_code_promotion_discussion_hint_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "rq_id": readiness.get("rq_id") or "RQ-029",
        "parent_rq": readiness.get("parent_rq") or "RQ-028",
        "promotion_discussion_eligible": summary.get("promotion_discussion_eligible"),
        "mechanical_ready": summary.get("mechanical_ready"),
        "human_signoff_status": summary.get("human_signoff_status"),
        "gate_decision": summary.get("gate_decision"),
        "operator_hint_ko": summary.get("operator_hint_ko"),
        "signoff": {
            "approved": signoff.get("approved"),
            "signoff_by": signoff.get("signoff_by"),
            "signoff_utc": signoff.get("signoff_utc"),
        },
        "track_wall": readiness.get("track_wall") or {},
        "boundary_ack": "승격 토의 가능 관측만. Track A·live·MS 압축 자동 합선 없음.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--webhook-env", type=str, default="MKM_A_CODE_PROMOTION_HINT_WEBHOOK_URL")
    parser.add_argument("--webhook-fallback-env", type=str, default="OPS_ALARM_WEBHOOK_URL")
    parser.add_argument("--webhook-url", type=str, default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    readiness = _read(args.readiness)
    if readiness.get("schema") != "a_code_promotion_checklist_readiness_v1":
        raise SystemExit(f"invalid readiness json: {args.readiness}")

    summary = readiness.get("summary") or {}
    eligible = summary.get("promotion_discussion_eligible") is True
    webhook = _resolve_webhook(args.webhook_env, args.webhook_fallback_env, args.webhook_url)

    dispatch_status = "skipped_not_eligible"
    http_status: int | None = None
    if eligible:
        body = build_dispatch_body(readiness)
        if not webhook:
            dispatch_status = "skipped_no_webhook"
        elif args.dry_run:
            dispatch_status = "dry_run"
        else:
            req = request.Request(
                webhook,
                data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=15) as resp:
                    http_status = resp.status
                dispatch_status = "posted"
            except error.HTTPError as e:
                http_status = e.code
                dispatch_status = f"http_error_{e.code}"
            except error.URLError as e:
                dispatch_status = f"url_error_{e.reason}"

    out_doc = {
        "schema": "a_code_promotion_discussion_hint_dispatch_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "non_gating": True,
        "promotion_discussion_eligible": eligible,
        "dispatch_status": dispatch_status,
        "http_status": http_status,
        "webhook_configured": bool(webhook),
        "readiness_source": (
            str(args.readiness.relative_to(ROOT)).replace("\\", "/")
            if args.readiness.is_relative_to(ROOT)
            else str(args.readiness)
        ),
        "summary": summary,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {args.out} eligible={eligible} dispatch={dispatch_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
