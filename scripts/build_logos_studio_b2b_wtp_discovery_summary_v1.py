#!/usr/bin/env python3
"""Aggregate WTP discovery call memos into summary JSON [HYPO].

Reads call status from markdown memos (completed + WTP checkboxes).
Reproduce:
  py scripts/build_logos_studio_b2b_wtp_discovery_summary_v1.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALL_DIR = ROOT / "reports"
CALL_GLOB = "logos_studio_b2b_wtp_discovery_call_{}_v1.md"
OUT = ROOT / "reports/logos_studio_b2b_wtp_discovery_summary_v1_latest.json"

WTP_PATTERNS = {
    3900000: re.compile(r"₩390만\s*수용|☑\s*₩390만|☒\s*₩390만"),
    4900000: re.compile(r"₩490만\s*수용|☑\s*₩490만|☒\s*₩490만"),
    5900000: re.compile(r"₩590만\s*수용|☑\s*₩590만|☒\s*₩590만"),
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_call(n: int) -> dict:
    path = CALL_DIR / CALL_GLOB.format(n)
    if not path.is_file():
        return {"call": n, "exists": False, "status": "missing"}
    text = path.read_text(encoding="utf-8")
    status = "completed" if "**Status:** `completed`" in text or "Status:** `completed`" in text else "pending"
    if "일시 |" in text:
        m = re.search(r"\|\s*일시\s*\|\s*([^\n|]+)", text)
        if m and m.group(1).strip():
            status = "completed" if m.group(1).strip() not in ("", "—", "-") else status
    accepted: list[int] = []
    for krw, pat in WTP_PATTERNS.items():
        if "☑" in text and pat.search(text):
            accepted.append(krw)
        elif re.search(rf"☑\s*₩{krw // 10000}만", text):
            accepted.append(krw)
    rejected = "☑" in text and "거절" in text and "☑ 거절" in text.replace(" ", "")
    return {
        "call": n,
        "exists": True,
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "status": status,
        "accepted_pilot_krw_hints": accepted,
        "rejected_hint": rejected,
    }


def main() -> int:
    calls = [_read_call(i) for i in (1, 2, 3)]
    completed = sum(1 for c in calls if c.get("status") == "completed")
    all_accepted: list[int] = []
    for c in calls:
        all_accepted.extend(c.get("accepted_pilot_krw_hints") or [])

    promotion = "research_only_until_3_calls_complete"
    if completed >= 3:
        if len(all_accepted) >= 2 and any(k >= 4900000 for k in all_accepted):
            promotion = "pricing_maturity_re_review_candidate"
        elif not all_accepted:
            promotion = "research_only_blockers_documented"

    out = {
        "schema": "logos_studio_b2b_wtp_discovery_summary_v1",
        "generated_at_utc": _utc(),
        "status": "partial" if completed else "awaiting_calls",
        "send_gate": "HOLD",
        "calls_completed": completed,
        "calls_required": 3,
        "template_md": "reports/logos_studio_b2b_wtp_discovery_memo_template_v1.md",
        "playbook_md": "reports/logos_studio_b2b_wtp_discovery_call_playbook_v1.md",
        "call_memos": [f"reports/logos_studio_b2b_wtp_discovery_call_{i}_v1.md" for i in (1, 2, 3)],
        "six_gate_bundle": "reports/logos_studio_b2b_pilot_six_gate_bundle_v1_latest.json",
        "pilot_sow": "reports/logos_studio_b2b_pilot_sow_1page_v1_latest.json",
        "pilot_price_band_krw_vat_excl": [3900000, 4900000, 5900000],
        "starter_monthly_band_krw_vat_excl": [1200000, 1500000, 1800000],
        "calls": calls,
        "aggregate": {
            "lowest_accepted_pilot_krw": min(all_accepted) if all_accepted else None,
            "highest_accepted_pilot_krw": max(all_accepted) if all_accepted else None,
            "starter_interest_krw": None,
            "common_blockers": [],
        },
        "promotion_decision": promotion,
        "reproduce": "py scripts/build_logos_studio_b2b_wtp_discovery_summary_v1.py",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "calls_completed": completed, "out": str(OUT)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
