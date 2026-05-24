#!/usr/bin/env python3
"""Record commander approval for Logos RAG B-track tier (audit only; tier-specific walls)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
REPORTS = ROOT / "reports"
DEFAULT_GATE = ART / "logos_rag_btrack_promotion_gate_v1_latest.json"
DEFAULT_OUT = ART / "logos_rag_btrack_promotion_human_approval_v1_latest.json"
DEFAULT_LOG = REPORTS / "logos_rag_btrack_promotion_approval_log_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tier", type=str, required=True, choices=["L1", "L2", "L3"])
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--approval-log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--reviewer", type=str, default="commander")
    ap.add_argument("--notes", type=str, default="")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Record even if gate not passed (explicit risk acceptance).",
    )
    args = ap.parse_args()

    gate_path = args.gate_json if args.gate_json.is_absolute() else ROOT / args.gate_json
    if not gate_path.is_file():
        raise SystemExit(f"Missing gate: {gate_path}")

    gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))
    tier_key = {
        "L1": "L1_btrack_lab_bundle",
        "L2": "L2_track_c_shadow_ingest",
        "L3": "L3_production_st_index",
    }[args.tier]
    tier = gate.get("tiers", {}).get(tier_key) or {}
    if not tier.get("approval_ready") and not args.force:
        raise SystemExit(
            f"Tier {args.tier} not approval_ready; fix gates or pass --force with explicit acceptance."
        )

    payload: dict[str, Any] = {
        "schema": "logos_rag_btrack_promotion_human_approval_v1",
        "ts_utc": _utc_now(),
        "tier": args.tier,
        "tier_key": tier_key,
        "decision": f"ACK_{args.tier}",
        "reviewer": args.reviewer,
        "notes": args.notes or f"Commander approved tier {args.tier} via chat.",
        "gate_snapshot": {
            "recommended_commander_action": gate.get("recommended_commander_action"),
            "metrics": gate.get("metrics"),
            "tier_passed": tier.get("passed"),
        },
        "track_wall": {
            "prophecy_promotion_gates_touch": False,
            "track_a_compression_touch": False,
            "use_gematria_4d_bridge": False if args.tier != "L3" else None,
            "a_track_live_trading": False,
            "promotion_to_a_track": args.tier == "L3",
        },
    }
    if args.tier == "L3":
        payload["track_wall"]["note"] = "L3 records intent only; ANN swap requires separate deploy runbook."

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    log_path = args.approval_log_jsonl if args.approval_log_jsonl.is_absolute() else ROOT / args.approval_log_jsonl
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")

    print(json.dumps({"ok": True, "tier": args.tier, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
