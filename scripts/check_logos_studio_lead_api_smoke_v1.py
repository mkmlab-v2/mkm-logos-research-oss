#!/usr/bin/env python3
"""Smoke: logos-research lead API (validation + dry submit).

Reproduce:
  py scripts/check_logos_studio_lead_api_smoke_v1.py --base https://logos.jema-ai.com
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/logos_studio_lead_api_smoke_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _post_json(url: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "MKM-LogosLeadApiSmoke/1.0",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return int(resp.status), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"ok": False, "error": body[:200]}
        return int(exc.code), parsed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://logos.jema-ai.com")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--require-webhook", action="store_true")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    lead_url = f"{base}/api/logos-research/lead"
    failures: list[str] = []

    bad_code, bad_body = _post_json(lead_url, {"email": "not-an-email"})
    if bad_code != 400 or bad_body.get("ok") is not False:
        failures.append(f"invalid_email_gate_{bad_code}")

    ok_code, ok_body = _post_json(
        lead_url,
        {
            "email": f"smoke+{int(datetime.now(timezone.utc).timestamp())}@example.com",
            "organization": "smoke-test",
            "note": "automated smoke — safe to ignore",
            "source": "logos-research-smoke-v1",
            "tier": "pilot",
        },
    )
    lead_id = ok_body.get("lead_id")
    webhook = ok_body.get("webhook") or {}
    if ok_code != 200 or not ok_body.get("ok") or not lead_id:
        failures.append(f"submit_failed_{ok_code}")
    if args.require_webhook:
        if not webhook.get("enabled"):
            failures.append("webhook_not_enabled")
        elif not webhook.get("delivered"):
            failures.append(f"webhook_not_delivered_{webhook.get('error', 'unknown')}")

    out_doc = {
        "schema": "logos_studio_lead_api_smoke_v1",
        "generated_at_utc": _utc(),
        "base": base,
        "ok": len(failures) == 0,
        "gate_failures": failures,
        "invalid_email_status": bad_code,
        "lead_id": lead_id,
        "webhook": webhook if ok_code == 200 else None,
        "reproduce": f"py scripts/check_logos_studio_lead_api_smoke_v1.py --base {base}",
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": out_doc["ok"], "gate_failures": failures, "out": str(out_path)}))
    return 0 if out_doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
