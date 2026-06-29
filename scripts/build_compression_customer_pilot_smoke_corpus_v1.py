#!/usr/bin/env python3
"""Synthetic customer-masked JSONL for customer pilot intake pipeline smoke (NOT real customer)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/compression/examples/customer_masked_pilot_smoke_v1.jsonl"

TEMPLATES = [
    "[masked] User ███ asked about refund policy for order ███. Agent explained 7-day window and escalation path.",
    "[masked] Ticket #███: billing discrepancy on invoice ███. Agent verified proration and issued credit memo draft.",
    "[masked] Customer ███ requested API rate limit increase from ███ to ███ req/min for staging environment.",
    "[masked] Chat: onboarding step 3 failed at SSO redirect. Agent suggested checking IdP metadata URL and clock skew.",
    "[masked] Prospect asked whether compression API preserves must-keep terms in contracts — agent cited overlay policy.",
    "[masked] User pasted log snippet with token ███ redacted; agent diagnosed timeout on webhook retry queue.",
    "[masked] Support thread: Korean FAQ about data residency — answer references region pin and DPA appendix.",
    "[masked] Agent summarized prior thread for handoff: issue=latency spike, region=ap-northeast, severity=P2.",
    "[masked] Customer asked for sandbox JSONL format for pilot ROI — agent sent schema with text field only.",
    "[masked] Escalation: repeated 403 on admin endpoint; root cause was expired service account key ███.",
    "[masked] User requested downgrade from enterprise tier; agent outlined 30-day notice and export window.",
    "[masked] B2B chat: legal asked for subprocessors list and retention defaults — agent linked trust pack index.",
    "[masked] Integration question: webhook signature validation failing — agent shared HMAC example without secrets.",
    "[masked] Customer ███ reported duplicate charges on ███; finance tag applied, case routed to billing queue.",
    "[masked] Agent explained difference between proxy token savings and contracted SLA — not a billing promise.",
    "[masked] User asked if Track A bench numbers apply to their corpus — agent clarified per-tenant measurement.",
    "[masked] Masked transcript: user frustration about slow dashboard; agent proposed cache warm and query index.",
    "[masked] Pre-sales: security questionnaire item 14 — encryption at rest and in transit summary for review.",
    "[masked] Customer pilot scope: 30 masked rows, SEND_GATE HOLD, 1:1 ROI proxy only until counsel sign-off.",
    "[masked] Agent closed loop: patch deployed to v2.3.1, monitoring dashboard link shared without credentials.",
    "[masked] User inquiry about GDPR erasure SLA — agent quoted standard 30-day window with verification steps.",
    "[masked] Chatbot log: intent=pricing, entities=seats ███, term=annual; agent sent tier comparison table.",
    "[masked] Technical deep-dive: must_keep overlay extraction from tenant corpus before routed compression PoC.",
    "[masked] Customer asked for Korean/English mixed support in compression — agent noted domain_tag routing.",
    "[masked] Incident follow-up: root cause memory leak in worker ███; mitigation rolled out to all tenants.",
    "[masked] User requested sample JSONL row — agent provided masked example with PII placeholders only.",
    "[masked] Partner channel: reseller ███ needs co-branded intake kit — internal review required before send.",
    "[masked] Agent reminder: public-open-web sandbox scores must not merge with customer pilot headlines.",
    "[masked] Final message: thanks for pilot data upload; next step run customer intake one-click script.",
    "[masked] Ops note: counsel sign-off required before ready_for_external_send flips from false.",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--rows", type=int, default=30)
    args = ap.parse_args()

    rows = []
    for i in range(args.rows):
        text = TEMPLATES[i % len(TEMPLATES)]
        rows.append(
            {
                "id": f"customer-smoke-{i:03d}",
                "text": text,
                "domain_tag": "customer-support-chat",
                "labels": ["synthetic_smoke", "masked", "pilot_only", "not_real_customer"],
                "customer_provided": False,
                "synthetic_smoke": True,
            }
        )

    out = args.out_jsonl.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "rows": len(rows), "out_jsonl": out.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
