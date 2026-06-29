#!/usr/bin/env python3
"""POST patient intake dry notification to test webhook (no Solapi live API)."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRY = ROOT / "docs/final/artifacts/patient_intake_solapi_dry_v1_latest.json"
PROBE_OUT = ROOT / "reports/patient_intake_notification_probe_v1_latest.json"


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Skip HTTP; report configured URLs only")
    ap.add_argument(
        "--include-ops-fallback",
        action="store_true",
        help="Also try OPS_ALARM_WEBHOOK_URL when dedicated intake URLs unset",
    )
    ap.add_argument(
        "--non-fatal",
        action="store_true",
        help="Exit 0 even if webhook POST fails (internal PoC chain)",
    )
    args = ap.parse_args()

    _load_dotenv()
    urls = [
        ("PATIENT_INTAKE_SOLAPI_TEST_WEBHOOK_URL", (os.environ.get("PATIENT_INTAKE_SOLAPI_TEST_WEBHOOK_URL") or "").strip()),
        ("KAKAO_CLINIC_INTAKE_WEBHOOK_URL", (os.environ.get("KAKAO_CLINIC_INTAKE_WEBHOOK_URL") or "").strip()),
    ]
    if args.include_ops_fallback:
        ops_fallback = (os.environ.get("OPS_ALARM_WEBHOOK_URL") or "").strip()
        if ops_fallback and not any(u for _, u in urls if u):
            urls.append(("OPS_ALARM_WEBHOOK_URL", ops_fallback))
    configured = [(name, url) for name, url in urls if url]

    if not DRY.is_file():
        print(json.dumps({"ok": False, "error": f"missing {DRY}"}))
        return 2

    dry_doc = json.loads(DRY.read_text(encoding="utf-8"))
    sample = (dry_doc.get("templates_dry") or [{}])[0]
    body = {
        "event": "patient_intake_notification_dry_v1",
        "lane": "internal_poc",
        "live_send": False,
        "template_key": sample.get("template_key"),
        "resolved_preview": sample.get("resolved_body"),
        "solapi_request_shape": sample.get("solapi_request_shape"),
    }

    if args.dry_run:
        print(
            json.dumps(
                {
                    "ok": True,
                    "configured_webhooks": [n for n, _ in configured],
                    "skipped_http": True,
                },
                ensure_ascii=False,
            )
        )
        return 0

    if not configured:
        result = {
            "ok": True,
            "delivered": False,
            "reason": "no_webhook_configured",
            "hint": "Set PATIENT_INTAKE_SOLAPI_TEST_WEBHOOK_URL or KAKAO_CLINIC_INTAKE_WEBHOOK_URL in .env",
        }
        PROBE_OUT.parent.mkdir(parents=True, exist_ok=True)
        PROBE_OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0

    results = []
    ok = True
    for name, url in configured:
        req = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                results.append({"env": name, "delivered": 200 <= res.status < 300, "status": res.status})
        except urllib.error.HTTPError as exc:
            ok = False
            results.append({"env": name, "delivered": False, "status": exc.code, "error": str(exc)})
        except OSError as exc:
            ok = False
            results.append({"env": name, "delivered": False, "error": str(exc)})

    print(json.dumps({"ok": ok, "results": results}, ensure_ascii=False))
    artifact = {
        "schema": "patient_intake_notification_probe_v1",
        "ok": ok,
        "live_send": False,
        "lane": "internal_poc",
        "results": results,
        "reproduce": "py scripts/probe_patient_intake_notification_webhook_v1.py",
    }
    PROBE_OUT.parent.mkdir(parents=True, exist_ok=True)
    PROBE_OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.non_fatal and not ok:
        print(json.dumps({**artifact, "non_fatal": True}, ensure_ascii=False))
        return 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
