#!/usr/bin/env python3
"""Synthetic masked enterprise JSONL for Tactical B free-audit pilot rehearsal.

NOT real customer data. Longer multi-turn support threads for intake plumbing proof.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/compression/tactical_b_free_audit_pilot_v1.jsonl"
META_OUT = ROOT / "reports/compression_tactical_b_free_audit_corpus_build_v1_latest.json"

THREADS: list[tuple[str, str]] = [
    (
        "customer-support-chat",
        "[masked] User ███ opened ticket T-88421: monthly invoice shows duplicate line for seat tier Enterprise Plus. "
        "Agent verified contract amendment dated ███ and explained proration window. User asked whether compression API "
        "metering counts input tokens only or includes system prompts. Agent clarified pilot measures proxy on masked JSONL only.",
    ),
    (
        "developer-support",
        "[masked] Integration thread: staging webhook returns 429 after batch compress calls. User pasted redacted headers "
        "and latency histogram. Agent suggested exponential backoff, idempotency keys, and separate economy vs fidelity SKU. "
        "Reminder: SEND_GATE HOLD until counsel sign-off on external savings claims.",
    ),
    (
        "security-review",
        "[masked] Security questionnaire §12: data residency, subprocessors, encryption at rest. Legal contact ███ requested "
        "sample DPA appendix and retention defaults. Agent linked trust pack index without internal paths. "
        "Customer asked if dogfood or Golden40 bench substitutes for their corpus — answer: per-tenant measurement required.",
    ),
    (
        "b2b-evaluation",
        "[masked] Pre-sales: prospect compares MKM token-path compression vs zstd on log archives. Agent explained path "
        "separation — byte codec bench is research_only and not interchangeable KPI. Offered free masked JSONL audit (20–50 rows) "
        "with 1:1 ROI proxy receipt; no SLA until contract.",
    ),
    (
        "ops-incident",
        "[masked] P2 incident: dashboard latency spike during routed PoC batch. On-call ███ noted worker memory growth. "
        "Mitigation: scale workers, warm cache, review must_keep overlay size. Postmortem draft excludes customer identifiers.",
    ),
    (
        "customer-support-chat",
        "[masked] Refund policy thread for order ███. User disputed 7-day window citing enterprise MSA clause 4.2. "
        "Agent escalated to billing queue with finance tag. Compression pilot scope unchanged: proxy only, not billing commitment.",
    ),
    (
        "developer-support",
        "[masked] API question: how to format customer JSONL for intake — single text field, domain_tag optional, 20–50 rows. "
        "User uploaded sample with PII placeholders. Agent validated row count and ran bootstrap tenant slug rehearsal offline.",
    ),
    (
        "b2b-evaluation",
        "[masked] CFO attendee asked for Jaccard vs semantic drift guarantees. Agent: lexical proxy + human review gate; "
        "forbidden to cite repair_v2 uplift as Track A promotion. Shared comparison_summary path label only, no attachment.",
    ),
    (
        "security-review",
        "[masked] Privacy review: confirm attached JSONL stripped emails, order IDs, API keys. DPO ███ approved pilot scope. "
        "External send remains false until apply_compression_b2b_legal_send_signoff with counsel acknowledge.",
    ),
    (
        "customer-support-chat",
        "[masked] Korean/English mixed support chat about onboarding step 5 — SSO metadata mismatch. "
        "Agent provided checklist: IdP clock skew, redirect URI, certificate expiry. User confirmed resolution; case closed.",
    ),
    (
        "developer-support",
        "[masked] Rate limit increase request from ███ req/min to ███ for load test. Approved for sandbox only. "
        "User asked about MKM-CHAT-D1 economy profile defaults and must_keep overlay extraction order.",
    ),
    (
        "b2b-evaluation",
        "[masked] Partner reseller ███ needs co-branded one-pager. Internal review required — public_open_web sandbox scores "
        "must not merge with customer pilot headlines. Tier_0 copy only until counsel.",
    ),
    (
        "ops-incident",
        "[masked] Follow-up on worker patch v2.3.1: memory leak fixed, monitoring green 24h. Customer ███ notified without credentials. "
        "Compression pilot artifacts remain research_only.",
    ),
    (
        "customer-support-chat",
        "[masked] User frustration: slow export of pilot ROI JSON. Agent explained local regeneration via one-click script. "
        "Clarified negative list-price proxy can occur on mixed corpus — not a savings headline.",
    ),
    (
        "security-review",
        "[masked] GDPR erasure request for user ███. Standard 30-day verification workflow started. "
        "Compression logs in pilot tenant excluded from production retention policy until contract.",
    ),
    (
        "b2b-evaluation",
        "[masked] Procurement asked for SOC2 overview and pilot timeline. Agent: 2-week masked JSONL intake, routed PoC, "
        "USD/KRW proxy receipt; human sign-off before ready_for_external_send.",
    ),
    (
        "developer-support",
        "[masked] Webhook signature validation failing — HMAC example shared without secrets. User fixed canonical string order. "
        "Secondary question on graph_wire_selective_bridge default false for economy profile.",
    ),
    (
        "customer-support-chat",
        "[masked] Downgrade from enterprise to team tier. 30-day notice, export window, no automatic compression SLA carryover. "
        "User acknowledged proxy metrics are tenant-specific.",
    ),
    (
        "b2b-evaluation",
        "[masked] Comparison to prior vendor quote: prospect wants 30% token savings guarantee. Agent declined guarantee; "
        "offered measured proxy on customer masked corpus with boundary_ack disclaimers.",
    ),
    (
        "ops-incident",
        "[masked] False positive alert on metering band 40–50% events. Triage: demo-seed rows in pilot log conflated with production. "
        "Recommendation: separate tenant slug per rehearsal.",
    ),
    (
        "security-review",
        "[masked] Subprocessor addendum review for EU customer ███. Legal hold on external send. "
        "Trust pack lists categories only — no internal repo paths in customer email.",
    ),
    (
        "customer-support-chat",
        "[masked] Chatbot intent=pricing, entities=seats ███, term=annual. Agent sent tier table without Track A 47% headline. "
        "Dogfood v2 ~17% proxy cited as internal only if at all — counsel first.",
    ),
    (
        "developer-support",
        "[masked] Sample JSONL row request fulfilled with masked placeholders. User asked max cases 30 vs 24 — either OK if >=20. "
        "RelaxPassGate is pilot-only smoke, not production gate.",
    ),
    (
        "b2b-evaluation",
        "[masked] Final pilot handoff: thanks for upload, next step Run-CompressionCustomerPilotIntake with tenant slug. "
        "SEND_GATE HOLD; counsel before customer-facing savings percentage.",
    ),
    (
        "customer-support-chat",
        "[masked] Closing loop: user confirmed pilot JSONL received. Agent scheduled internal review with compression_cfo_briefing "
        "pointer — no automatic Vault mirror; manual G: copy on commander approval.",
    ),
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_rows(target: int = 25) -> list[dict]:
    rows: list[dict] = []
    for i in range(target):
        domain_tag, text = THREADS[i % len(THREADS)]
        rows.append(
            {
                "id": f"tactical-b-audit-{i:03d}",
                "text": text,
                "domain_tag": domain_tag,
                "labels": ["synthetic_masked", "tactical_b", "free_audit_rehearsal", "not_real_customer"],
                "customer_provided": False,
                "tactical_b": True,
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-json", type=Path, default=META_OUT)
    ap.add_argument("--rows", type=int, default=25)
    args = ap.parse_args()
    rows = build_rows(args.rows)
    out = args.out_jsonl if args.out_jsonl.is_absolute() else ROOT / args.out_jsonl
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    lens = [len(r["text"]) for r in rows]
    meta = {
        "schema": "compression_tactical_b_free_audit_corpus_build_v1",
        "generated_at_utc": _utc(),
        "row_count": len(rows),
        "char_len_mean": round(sum(lens) / len(lens), 1),
        "tenant_recommendation": "tactical-b-free-audit-v1",
        "labels": ["tactical_b", "synthetic_masked", "free_audit_rehearsal", "send_gate_hold"],
        "out_jsonl": str(out.relative_to(ROOT)).replace("\\", "/"),
    }
    meta_path = args.meta_json if args.meta_json.is_absolute() else ROOT / args.meta_json
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, **meta}, ensure_ascii=False))
    return 0 if len(rows) >= 20 else 1


if __name__ == "__main__":
    raise SystemExit(main())
