#!/usr/bin/env python3
"""Write operator handoff when Cloudflare Email Routing API is blocked or zone missing."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    forward_to = os.environ.get("MKM_MKMLIFE_SUPPORT_FORWARD_TO", "moksorinw@gmail.com").strip()
    out = root / "reports" / "email_forward_setup_handoff_latest.json"
    payload = {
        "schema": "email_forward_setup_handoff_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "forward_to": forward_to,
        "status_pointer": "reports/email_forward_status_latest.json",
        "api_token_email_routing": "blocked_403_authentication_error",
        "routes": [
            {
                "custom_address": "support@mkmlife.com",
                "apex": "mkmlife.com",
                "zone_id_fixture": "259a847ea3643566383972ebd3ede918",
                "dashboard_status": "rule_enabled_destination_moksorinw",
                "note": "MX on Cloudflare; support@ rule edited in dashboard 2026-05-19.",
            },
            {
                "custom_address": "admin@no1kmedi.com",
                "apex": "no1kmedi.com",
                "zone_id": "1516522160411707c33f84e145416a53",
                "cloudflare_account_id": "646e42cf881ab43043c32430e99d9af4",
                "dashboard_status": "verified_by_user_inbox_test",
                "note": "User confirmed test mail to admin@ arrived at Gmail.",
            },
        ],
        "dashboard_steps": [
            f"Done: both apex MX → Cloudflare. Inbox = {forward_to} only.",
            "Optional: send test to support@mkmlife.com (admin@ already verified).",
        ],
        "common_mistake": "admin@no1kmedi.com in 'Destination addresses' shows 'verification pending' — that verifies admin inbox, not forwarding. Remove it; add admin@ under no1kmedi.com zone Routing rules instead.",
        "token_fix": [
            "Create API token: Account · Email Routing Addresses · Edit; Zone · Email Routing Rules · Edit; Zone · Read.",
            "Include zones no1kmedi.com and mkmlife.com (if on same account).",
            "Update CLOUDFLARE_API_TOKEN in .env → sync_required_env_to_user.ps1 → re-run Invoke-MkmInboundEmailForwardSetup_v1.ps1",
        ],
        "workspace_mx_note": "If no1kmedi.com apex MX is Google Workspace only, set admin@ forwarding in Google Admin instead of Cloudflare.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
