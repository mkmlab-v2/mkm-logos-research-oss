#!/usr/bin/env python3
"""Send inbound probe to Cloudflare Email Routing MX (no API token needed)."""
from __future__ import annotations

import json
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path


def main() -> int:
    to_addr = "moksorinw@no1kmedi.com"
    subject = f"MKM CF routing probe {datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    body = (
        "Automated delivery probe from scripts/send_no1kmedi_email_routing_inbound_probe_v1.py\n"
        "If this arrives at moksorinw@gmail.com, Cloudflare routing works.\n"
    )
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "routing-probe@no1kmedi.com"
    msg["To"] = to_addr
    msg.set_content(body)

    mx_hosts = ["route1.mx.cloudflare.net", "route2.mx.cloudflare.net", "route3.mx.cloudflare.net"]
    log: dict = {"schema": "email_routing_inbound_probe_v1", "to": to_addr, "attempts": []}
    last_err = None
    for mx in mx_hosts:
        row = {"mx": mx}
        try:
            with smtplib.SMTP(mx, 25, timeout=45) as smtp:
                smtp.ehlo()
                refused = smtp.send_message(msg)
                row["refused"] = refused
                row["ok"] = not refused
                log["attempts"].append(row)
                if not refused:
                    log["result"] = "accepted_by_mx"
                    log["subject"] = subject
                    out = Path(__file__).resolve().parents[1] / "reports" / "email_routing_inbound_probe_latest.json"
                    out.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"OK: accepted by {mx}; check Gmail for subject: {subject}")
                    return 0
        except Exception as e:
            row["ok"] = False
            row["error"] = str(e)
            log["attempts"].append(row)
            last_err = e
    log["result"] = "all_mx_failed"
    log["last_error"] = str(last_err)
    out = Path(__file__).resolve().parents[1] / "reports" / "email_routing_inbound_probe_latest.json"
    out.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"FAIL: {last_err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
