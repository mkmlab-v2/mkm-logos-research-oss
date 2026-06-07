#!/usr/bin/env python3
"""Synthesize DSS/apocrypha insight brief from quality + fusion reports (metadata only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hebrew_primary(quality: dict[str, Any]) -> int:
    if "hebrew_primary_tokens" in quality:
        return int(quality["hebrew_primary_tokens"])
    tiers = quality.get("lineage_tier_counts") if isinstance(quality.get("lineage_tier_counts"), dict) else {}
    return int(tiers.get("A_HEBREW_PRIMARY") or 0)


def _translation_proxy_ratio(quality: dict[str, Any]) -> float:
    if "translation_proxy_ratio" in quality:
        return float(quality["translation_proxy_ratio"])
    tiers = quality.get("lineage_tier_counts") if isinstance(quality.get("lineage_tier_counts"), dict) else {}
    total = int(quality.get("total_tokens") or 0)
    proxy = int(tiers.get("C_TRANSLATION_PROXY") or 0)
    return round(proxy / total, 6) if total else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--quality-json", type=Path, required=True)
    ap.add_argument("--fusion-quality-json", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--out-md", type=Path, default=None)
    args = ap.parse_args()

    quality = _load(args.quality_json) if args.quality_json.is_file() else {}
    fusion = _load(args.fusion_quality_json) if args.fusion_quality_json.is_file() else {}

    hebrew = _hebrew_primary(quality)
    proxy_ratio = _translation_proxy_ratio(quality)
    fusion_overlap = float(fusion.get("overlap_ratio_dss") or 0.0)
    fusion_pass = str(fusion.get("status") or "").upper() == "PASS"

    payload = {
        "schema": "dss_apocrypha_insight_brief_v1",
        "generated_at_utc": _utc_now(),
        "tag": args.tag,
        "pilot_insight_ready": fusion_pass and hebrew > 0,
        "authority_ready": False,
        "sources": {
            "quality_json": str(args.quality_json),
            "fusion_quality_json": str(args.fusion_quality_json),
        },
        "metrics": {
            "hebrew_primary_tokens": hebrew,
            "translation_proxy_ratio": proxy_ratio,
            "fusion_overlap_ratio_dss": fusion_overlap,
            "fusion_status": fusion.get("status"),
            "total_tokens": quality.get("total_tokens"),
        },
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.out_md is not None:
        md = (
            f"# DSS Apocrypha insight brief ({args.tag})\n\n"
            f"- pilot_insight_ready: {payload['pilot_insight_ready']}\n"
            f"- hebrew_primary_tokens: {hebrew}\n"
            f"- translation_proxy_ratio: {proxy_ratio}\n"
            f"- fusion_overlap_ratio_dss: {fusion_overlap}\n"
        )
        args.out_md.write_text(md, encoding="utf-8")

    print(f"pilot_insight_ready={payload['pilot_insight_ready']}")
    print(f"authority_ready={payload['authority_ready']}")
    print(f"json={args.out_json}")
    if args.out_md:
        print(f"md={args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
