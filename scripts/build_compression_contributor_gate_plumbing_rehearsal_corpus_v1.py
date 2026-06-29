#!/usr/bin/env python3
"""Build gate-plumbing rehearsal JSONL (long structured rows; NOT canonical example SSOT)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/compression/examples/compression_contributor_gate_plumbing_rehearsal_v1.jsonl"

DOMAINS = (
    "open-api-telemetry",
    "open-api-inventory",
    "open-api-payments",
    "open-api-auth",
    "open-api-search",
    "open-api-webhooks",
    "open-api-billing",
    "open-api-exports",
    "open-api-ingest",
    "open-api-alerts",
    "open-api-quotas",
    "open-api-audit",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _long_payload(batch: int, domain_tag: str) -> str:
    events: list[dict[str, Any]] = []
    base = batch * 100
    for i in range(12):
        events.append(
            {
                "seq": base + i,
                "service": domain_tag,
                "method": "POST",
                "path": f"/v1/resource/{batch}",
                "status": 429 if i % 5 == 0 else 200,
                "latency_ms": 20 + i * 3,
                "request_id": f"req_{batch:04d}_{i:02d}",
                "tenant": "open-bench-contributor",
                "attributes": {
                    "region": "ap-northeast-2",
                    "cache": "miss" if i % 4 == 0 else "hit",
                    "bytes_in": 400 + i * 17,
                    "bytes_out": 180 + i * 9,
                },
            }
        )
    doc = {
        "schema": "open_structured_long_v1",
        "batch": batch,
        "domain_tag": domain_tag,
        "events": events,
        "footer": "gate_plumbing_rehearsal_only_not_moat_quality_proof",
    }
    return json.dumps(doc, ensure_ascii=False)


def _row(batch: int, domain_tag: str) -> dict[str, Any]:
    return {
        "id": f"contrib-plumbing-{batch:03d}",
        "text": _long_payload(batch, domain_tag),
        "domain_tag": domain_tag,
        "labels": [
            "contributor_provided",
            "research_only",
            "btrack_learning_v1",
            "gate_plumbing_rehearsal",
            "masked",
            "not_customer_data",
        ],
        "contributor_provided": True,
        "customer_provided": False,
        "rehearsal_only": True,
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "boundary_ack": "Pipeline E2E rehearsal only; not GitHub Moat or Track A quality claim.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--rows", type=int, default=12)
    args = ap.parse_args()

    lines: list[str] = []
    for i in range(args.rows):
        domain = DOMAINS[i % len(DOMAINS)]
        lines.append(json.dumps(_row(i + 1, domain), ensure_ascii=False))

    out = args.out_jsonl.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "generated_at_utc": _utc(),
                "out_jsonl": str(out).replace("\\", "/"),
                "rows": len(lines),
                "rehearsal_only": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
