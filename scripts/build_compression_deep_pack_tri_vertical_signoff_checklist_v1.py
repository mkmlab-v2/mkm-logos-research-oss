#!/usr/bin/env python3
"""Build tri-vertical deep pack commander rollup signoff checklist.

Aggregates zone_f_code (ZF_MASK), zone_h_en_business (BIZ_MASK), zone_ko_premium_cs (CS_MASK).
research_only · SEND_GATE HOLD · no ACTIVE mutation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CODING_CHECKLIST = ROOT / "docs/final/artifacts/compression_coding_deep_pack_signoff_checklist_v1_latest.json"
EN_BUSINESS_CHECKLIST = ROOT / "docs/final/artifacts/compression_en_business_deep_pack_signoff_checklist_v1_latest.json"
KO_CS_CHECKLIST = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_signoff_checklist_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/compression_deep_pack_tri_vertical_signoff_checklist_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_checklist(
    *,
    coding_path: Path,
    en_business_path: Path,
    ko_cs_path: Path,
) -> dict[str, Any]:
    coding = _load(coding_path)
    en_biz = _load(en_business_path)
    ko_cs = _load(ko_cs_path)

    verticals = {
        "zone_f_code": {
            "wire_family": "ZF_MASK",
            "checklist": coding,
            "artifact": _rel(coding_path),
        },
        "zone_h_en_business_v1": {
            "wire_family": "BIZ_MASK",
            "checklist": en_biz,
            "artifact": _rel(en_business_path),
        },
        "zone_ko_premium_cs_v1": {
            "wire_family": "CS_MASK",
            "checklist": ko_cs,
            "artifact": _rel(ko_cs_path),
        },
    }

    wire_families = {v["wire_family"] for v in verticals.values()}
    per_vertical_green = {
        vid: bool(v["checklist"].get("all_green")) and v["checklist"].get("decision") == "READY_FOR_COMMANDER_SIGNOFF"
        for vid, v in verticals.items()
    }

    checklist = {
        "coding_pack_ready": per_vertical_green["zone_f_code"],
        "en_business_pack_ready": per_vertical_green["zone_h_en_business_v1"],
        "ko_premium_cs_pack_ready": per_vertical_green["zone_ko_premium_cs_v1"],
        "all_three_verticals_ready": all(per_vertical_green.values()),
        "wire_families_distinct": wire_families == {"ZF_MASK", "BIZ_MASK", "CS_MASK"},
        "research_only_all": all(
            bool(v["checklist"].get("research_only")) for v in verticals.values()
        ),
        "send_gate_hold_all": all(
            str(v["checklist"].get("send_gate") or "").upper() == "HOLD" for v in verticals.values()
        ),
        "track_a_active_untouched_all": all(
            bool(v["checklist"].get("track_a_active_untouched")) for v in verticals.values()
        ),
        "human_signoff_not_applied_any": all(
            bool(v["checklist"].get("checklist", {}).get("human_signoff_not_applied"))
            for v in verticals.values()
        ),
        "fail_comp_axis_separation_ack": True,
    }
    failed = [k for k, v in checklist.items() if not v]
    all_green = len(failed) == 0
    decision = "READY_FOR_COMMANDER_SIGNOFF" if all_green else "HOLD_NEEDS_REVIEW"

    return {
        "schema": "compression_deep_pack_tri_vertical_signoff_checklist_v1",
        "generated_at_utc": _utc(),
        "decision": decision,
        "all_green": all_green,
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "verticals": {
            vid: {
                "wire_family": meta["wire_family"],
                "decision": meta["checklist"].get("decision"),
                "all_green": meta["checklist"].get("all_green"),
                "checklist_artifact": meta["artifact"],
            }
            for vid, meta in verticals.items()
        },
        "checklist": checklist,
        "failed_checks": failed,
        "constraints": {
            "human_review_required": True,
            "automatic_active_swap": False,
            "b_to_a_auto_bridge": False,
            "headline_merge_forbidden": "FAIL-COMP-004",
        },
        "commander_review_items": [
            "Three wire families (ZF_MASK / BIZ_MASK / CS_MASK) remain separate axes.",
            "Each vertical twin gate uses saving_rate + exact_restore_ok — not Jaccard alone.",
            "KO CS CS_MASK requires ███ mask exact-restore; wtt shortcap stays hybrid-router only.",
            "Rollup approves research envelopes only; ACTIVE swap requires separate Track A gate.",
        ],
        "reproduce": [
            "py scripts/build_compression_coding_deep_pack_signoff_checklist_v1.py",
            "py scripts/build_compression_en_business_deep_pack_gate_v1.py",
            "py scripts/build_compression_ko_premium_cs_deep_pack_gate_v1.py",
            "py scripts/build_compression_deep_pack_tri_vertical_signoff_checklist_v1.py",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build tri-vertical deep pack rollup signoff checklist")
    ap.add_argument("--coding-checklist", type=Path, default=CODING_CHECKLIST)
    ap.add_argument("--en-business-checklist", type=Path, default=EN_BUSINESS_CHECKLIST)
    ap.add_argument("--ko-cs-checklist", type=Path, default=KO_CS_CHECKLIST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    for label, p in (
        ("coding", args.coding_checklist),
        ("en_business", args.en_business_checklist),
        ("ko_cs", args.ko_cs_checklist),
    ):
        if not p.is_file():
            print(f"MISSING {label} checklist: {p}", file=sys.stderr)
            return 1
    doc = build_checklist(
        coding_path=args.coding_checklist,
        en_business_path=args.en_business_checklist,
        ko_cs_path=args.ko_cs_checklist,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), "decision": doc["decision"], "all_green": doc["all_green"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
