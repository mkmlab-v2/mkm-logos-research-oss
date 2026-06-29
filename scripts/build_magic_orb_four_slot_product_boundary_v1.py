#!/usr/bin/env python3
"""SKU boundary SSOT — oracle-sphere public demo vs Ask One premium (B-track)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/magic_orb_four_slot_product_boundary_v1_latest.json"


def build() -> dict:
    return {
        "schema": "magic_orb_four_slot_product_boundary_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "track_a_blocked": True,
        "send_gate_default": "HOLD",
        "skus": {
            "oracle_sphere_public_demo": {
                "surface": "mkmlife.com/oracle-sphere",
                "price_tier": "free",
                "four_slot_source": "assembler_v1",
                "post_llm_fill": "optional_off_by_default",
                "commercial_claim": "research_showroom_only",
            },
            "ask_one_premium_report": {
                "surface": "mkmlife.com/ask-one",
                "price_tier": "paid_candidate",
                "four_slot_source": "assembler_v1_plus_post_llm_fill",
                "post_llm_fill": "tier_15_human_gate",
                "commercial_claim": "premium_research_report_not_track_a_core",
            },
        },
        "walls": {
            "no_track_a_auto_merge": True,
            "no_send_gate_open_without_human": True,
            "no_fact_locked_llm_without_verified_anchor": True,
            "no_why_causality_auto_assembly": True,
        },
        "reproduce": "py scripts/build_magic_orb_four_slot_product_boundary_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
