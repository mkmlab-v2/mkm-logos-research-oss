#!/usr/bin/env python3
"""Evaluate DSS authority readiness from insight brief + fusion metrics (B-track metadata only)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--insight-brief-json", type=Path, required=True)
    ap.add_argument("--min-hebrew-primary-tokens", type=int, default=500)
    ap.add_argument("--max-translation-proxy-ratio", type=float, default=0.8)
    ap.add_argument("--min-fusion-overlap-ratio-dss", type=float, default=0.02)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--out-md", type=Path, default=None)
    args = ap.parse_args()

    brief = _load(args.insight_brief_json) if args.insight_brief_json.is_file() else {}
    metrics = brief.get("metrics") if isinstance(brief.get("metrics"), dict) else {}

    hebrew = int(metrics.get("hebrew_primary_tokens") or 0)
    proxy_ratio = float(metrics.get("translation_proxy_ratio") or 0.0)
    fusion_overlap = float(metrics.get("fusion_overlap_ratio_dss") or 0.0)
    pilot_ready = bool(brief.get("pilot_insight_ready"))

    checks = {
        "pilot_insight_ready": pilot_ready,
        "hebrew_primary_tokens": hebrew >= args.min_hebrew_primary_tokens,
        "translation_proxy_ratio": proxy_ratio <= args.max_translation_proxy_ratio,
        "fusion_overlap_ratio_dss": fusion_overlap >= args.min_fusion_overlap_ratio_dss,
    }
    blocked = [k for k, ok in checks.items() if not ok]
    status = "READY" if not blocked else "BLOCKED"

    payload = {
        "status": status,
        "checks": checks,
        "thresholds": {
            "min_hebrew_primary_tokens": args.min_hebrew_primary_tokens,
            "max_translation_proxy_ratio": args.max_translation_proxy_ratio,
            "min_fusion_overlap_ratio_dss": args.min_fusion_overlap_ratio_dss,
        },
        "metrics": {
            "hebrew_primary_tokens": hebrew,
            "translation_proxy_ratio": proxy_ratio,
            "fusion_overlap_ratio_dss": fusion_overlap,
        },
        "blocked_reasons": blocked,
        "tag": args.tag,
        "insight_brief_json": str(args.insight_brief_json),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.out_md is not None:
        lines = [
            f"# Authority readiness ({args.tag})",
            "",
            f"- status: **{status}**",
            f"- hebrew_primary_tokens: {hebrew}",
            f"- translation_proxy_ratio: {proxy_ratio}",
            f"- fusion_overlap_ratio_dss: {fusion_overlap}",
        ]
        if blocked:
            lines.append(f"- blocked_reasons: {', '.join(blocked)}")
        args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"status={status}")
    print(f"json={args.out_json}")
    if args.out_md:
        print(f"md={args.out_md}")
    return 0 if status == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
