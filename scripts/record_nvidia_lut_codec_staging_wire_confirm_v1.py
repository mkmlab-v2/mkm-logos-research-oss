#!/usr/bin/env python3
"""[HYPO] Commander confirms LUT→codec staging wire (product lane only, no ACTIVE core)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LUT = ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_LUT_DRAFT_V1.json"
STAGING_REVIEW = ROOT / "reports/nvidia_lut_codec_staging_review_v1_latest.json"
SIGNOFF = ROOT / "reports/nvidia_de_nim_commander_anchor_signoff_v1_latest.json"
CODEC_MANIFEST = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_codec_bench_split_manifest_v1_latest.json"
)
OUT = ROOT / "reports/nvidia_lut_codec_staging_wire_confirm_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _wire_block(block: dict[str, Any], accepted: set[str]) -> None:
    block["wired_into_codec"] = True
    block["codec_wire_mode"] = "staging_product_lane_only_v1"
    block["track_a_active_write"] = False
    by_probe = block.get("candidates_by_probe_id") or {}
    for pid, row in by_probe.items():
        if not isinstance(row, dict):
            continue
        if pid in accepted:
            row["codec_staging_wired"] = True
            row["codec_wire_lane"] = "hybrid_sidecar_preview"
        else:
            row["codec_staging_wired"] = False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-by", default="commander")
    ap.add_argument(
        "--hold",
        action="store_true",
        help="Record hold decision without wiring",
    )
    args = ap.parse_args()

    review = (
        json.loads(STAGING_REVIEW.read_text(encoding="utf-8-sig"))
        if STAGING_REVIEW.is_file()
        else {}
    )
    signoff = (
        json.loads(SIGNOFF.read_text(encoding="utf-8-sig")) if SIGNOFF.is_file() else {}
    )
    if not review and not args.hold:
        print(json.dumps({"error": "missing_staging_review"}))
        return 2

    sv = review.get("staging_verdict") or {}
    if not args.hold and not sv.get("product_lane_ready"):
        print(
            json.dumps(
                {
                    "error": "product_lane_not_ready",
                    "verdict": sv,
                },
                ensure_ascii=False,
            )
        )
        return 2

    accepted = set(signoff.get("accepted_probe_ids") or [])
    doc = {
        "schema": "nvidia_lut_codec_staging_wire_confirm_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "signoff_by": args.signoff_by,
        "decision": "hold" if args.hold else "confirm_product_lane_staging_wire",
        "codec_wired_staging": not args.hold,
        "track_a_active_write": False,
        "recommended_lane": sv.get("recommended_primary_lane"),
        "latent_active_replacement_ready": sv.get("latent_active_replacement_ready"),
        "accepted_probe_ids": sorted(accepted),
        "forbidden": ["--apply-active", "auto_merge_into_active_codec"],
    }

    if LUT.is_file() and not args.hold:
        lut = json.loads(LUT.read_text(encoding="utf-8-sig"))
        for key in ("de_probe_staging_v1", "nim_anchor_staging_v1"):
            block = lut.get(key)
            if isinstance(block, dict):
                _wire_block(block, accepted)
        lut["lut_codec_staging_wire_v1"] = {
            "confirmed_at_utc": _utc(),
            "confirmed_by": args.signoff_by,
            "lane": "hybrid_sidecar_preview",
            "keep_ratio": 0.88,
            "codec_manifest_pointer": str(CODEC_MANIFEST.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "wired_into_codec": True,
            "semantic": "staging_metadata_only_not_active_core",
            "track_a_active_write": False,
        }
        lut["codec_wired_staging"] = True
        lut["track_a_active_write"] = False
        LUT.write_text(json.dumps(lut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if STAGING_REVIEW.is_file() and not args.hold:
        review["codec_wired"] = True
        review["codec_wired_staging_only"] = True
        review["human_next"] = "staging_wire_complete_monitor_b2b_product_lane"
        STAGING_REVIEW.write_text(
            json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "decision": doc["decision"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
