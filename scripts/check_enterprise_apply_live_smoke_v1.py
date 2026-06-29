#!/usr/bin/env python3
"""API-level smoke for app.jema-ai.com/enterprise/apply (no Turnstile bypass)."""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/enterprise_apply_live_smoke_v1_latest.json"
APPLY_URL = "https://app.jema-ai.com/enterprise/apply"
API_URL = "https://app.jema-ai.com/api/leads/compression-pilot-audit"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "MKM-enterprise-apply-smoke/1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return int(resp.status), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return int(e.code), body


def _post_json(url: str, payload: dict[str, Any]) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "MKM-enterprise-apply-smoke/1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return int(resp.status), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return int(e.code), body


def build() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    status, html = _get(APPLY_URL)
    checks.append({"id": "apply_page_reachable", "ok": status == 200, "status": status})
    markers = ["compression", "apply", "company", "contact_email", "pii_scrub_ack"]
    found = [m for m in markers if m in html.lower()]
    checks.append({"id": "apply_page_form_markers", "ok": len(found) >= 4, "found": found})
    api_status, _ = _post_json(API_URL, {})
    checks.append({"id": "apply_api_route_exists", "ok": api_status in (400, 401, 403, 422), "status": api_status})
    _, api_body = _post_json(
        API_URL,
        {"company": "smoke", "contact_email": "smoke@example.com", "use_case": "test"},
    )
    turnstile_gate = "turnstile_token_required" in api_body
    checks.append(
        {
            "id": "apply_api_json_response",
            "ok": turnstile_gate,
            "sample": api_body[:200],
        }
    )
    all_ok = all(c.get("ok") for c in checks)
    return {
        "schema": "enterprise_apply_live_smoke_v1",
        "generated_at_utc": _utc(),
        "target": {"apply_url": APPLY_URL, "api_url": API_URL},
        "all_ok": all_ok,
        "decision": "PASS" if all_ok else "FAIL",
        "human_gate_note": "Full Turnstile form submit requires commander Tier-3 browser test",
        "checks": checks,
        "reproduce": "py scripts/check_enterprise_apply_live_smoke_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "decision": doc["decision"]}, ensure_ascii=False))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
