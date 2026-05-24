#!/usr/bin/env python3
"""One-page lab summary from golden_40_expansion_pool_compare (B-track, HOLD default)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "reports/golden_40_expansion_pool_compare_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/golden_40_expansion_lab_summary_v1_latest.json"
HEADLINE_POLICY = ROOT / "reports/compression_track_a_headline_policy_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    compare_path = args.compare_json if args.compare_json.is_absolute() else ROOT / args.compare_json
    doc = json.loads(compare_path.read_text(encoding="utf-8"))

    frozen: dict[str, Any] = {}
    if HEADLINE_POLICY.is_file():
        hp = json.loads(HEADLINE_POLICY.read_text(encoding="utf-8"))
        frozen = hp.get("frozen_headline_prior") or {}

    n400: dict[str, Any] = {}
    for mode, block in (doc.get("pools") or {}).items():
        for row in block.get("tier_summary") or []:
            if int(row.get("target") or 0) == 400:
                n400[mode] = row
                break

    out = {
        "schema": "golden_40_expansion_lab_summary_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "source_compare": str(compare_path.relative_to(ROOT)).replace("\\", "/"),
        "frozen_headline_ms_paste": frozen,
        "promotion_recommendation": "HOLD",
        "headline_kpi_update": "HOLD",
        "news_readiness": False,
        "would_change_active": False,
        "tier_n400_by_pool": n400,
        "findings": [
            "Golden core 40-case Jaccard stays ~0.873 across pools and N (lab).",
            "Expanded-N blended Jaccard != Golden 40 headline 0.890 — do not merge into MS paste.",
            "homogeneous_logos_verse N=400 reached; blended Jaccard ~0.745 (ancient text proxy).",
            "mixed_matrix dilutes faster than homogeneous_sasang_ko at N=80–120.",
            "FAIL-COMP-004: disk remeasure != promoted headline; human sign-off required.",
        ],
        "exit_codes": doc.get("exit_codes"),
    }

    out_path = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
