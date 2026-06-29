#!/usr/bin/env python3
"""Write company email 3-tier ops policy artifact."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "mkm_company_email_ops_policy_v1_latest.json"
INBOX = "moksorinw@gmail.com"


def main() -> int:
    payload = {
        "schema": "mkm_company_email_ops_policy_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inbox_hub": INBOX,
        "tiers": {
            "public_b2b": {
                "address": "support@mkmlife.com",
                "role_ko": "웹·푸터·B2B·엔터프라이즈 공식 문의",
                "ssot": "projects/no1kmedi/marketing-site/public-copy.json",
            },
            "ops_founder": {
                "address": "moksorinw@no1kmedi.com",
                "role_ko": "지휘관 실무·회사 도메인 개인 겸용",
                "forward_to": INBOX,
            },
            "workspace_internal": {
                "address": "admin@no1kmedi.com",
                "role_ko": "Google Workspace·NotebookLM MCP·클리닉 allowlist",
                "forward_to": INBOX,
            },
            "gcp_account": {
                "address": "jema12@mkmlife.com",
                "role_ko": "GCP/Vertex 로그인 전용 — 일반 회사 메일 아님",
                "forward_to": None,
            },
        },
        "outbound": {
            "morning_digest": {
                "transport": "Gmail SMTP (GMAIL_* secure store); Graph fallback; Hostinger legacy skip",
                "schedule": "MKM-Kospi-Morning-Email-Digest 08:28 KST",
                "telegram": "OFF",
                "style": "prophecy_slim_korean",
            },
            "hostinger_smtp": "expired — do not use",
            "send_as_support": "optional manual — Gmail Send mail as support@mkmlife.com",
        },
        "inbound_routing_ssot": "reports/email_forward_status_latest.json",
        "reproduce": "powershell -File scripts/Invoke-MkmCompanyEmailOpsPolicy_v1.ps1",
        "verify": "powershell -File scripts/Verify-KospiMorningEmailDigestReadiness_v1.ps1",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
