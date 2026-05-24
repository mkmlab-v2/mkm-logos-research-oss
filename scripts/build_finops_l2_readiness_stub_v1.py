#!/usr/bin/env python3
"""FinOps L2 readiness stub — human gates only (no auto L2 promotion)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / "docs/final/artifacts/finops_wire_domain_v1_closeout_official_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/finops_l2_readiness_stub_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_stub() -> dict[str, Any]:
    official = {}
    if OFFICIAL.is_file():
        official = json.loads(OFFICIAL.read_text(encoding="utf-8"))
    l1_ok = official.get("approval_status") == "APPROVED_COMMANDER"
    return {
        "ok": l1_ok,
        "schema": "finops_l2_readiness_stub_v1",
        "generated_at_utc": _utc(),
        "l1_official": l1_ok,
        "l2_ready": False,
        "l2_ready_reason": "legal_and_pilot_gates_pending",
        "human_gates": [
            {"id": "legal_before_external_send", "status": "pending", "owner": "counsel"},
            {"id": "optional_pilot_customer_corpus", "status": "pending", "owner": "commander"},
            {"id": "weekly_smoke_narrative_4_8w", "status": "pending", "owner": "calendar"},
        ],
        "automated_prerequisites_met": {
            "finops_domain_eval": True,
            "finops_l1_official_closeout": l1_ok,
            "rq_019_closed": True,
        },
        "forbidden_until_l2": [
            "external_send",
            "track_a_auto_promotion",
            "live_trading_trigger",
            "lossless_or_100_percent_claims",
        ],
        "official_pointer": OFFICIAL.relative_to(ROOT).as_posix(),
        "research_only": True,
        "boundary_ack": "Stub checklist only; L2 commercial readiness requires human gates.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_stub()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.out_json.resolve())}))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
