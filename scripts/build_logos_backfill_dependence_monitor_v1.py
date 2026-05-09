#!/usr/bin/env python3
"""Build monitor report for backfill dependence delta."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_COMPARE = ART / "logos_temporal_holdout_compare_backfill_latest.json"
DEFAULT_OUT = ART / "logos_backfill_dependence_monitor_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build backfill dependence monitor report.")
    ap.add_argument("--compare-json", type=Path, default=DEFAULT_COMPARE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-allowed-delta", type=float, default=0.15)
    args = ap.parse_args()

    doc = _load_json(args.compare_json)
    pure = (doc.get("pure_real") or {}).get("corr_candidate_resonance_vs_non_synthetic_hit_rate_eligible_only")
    mixed = (doc.get("mixed_backfill") or {}).get("corr_candidate_resonance_vs_non_synthetic_hit_rate_eligible_only")
    delta = doc.get("delta_mixed_minus_pure")

    status = "UNKNOWN"
    if delta is None:
        status = "INSUFFICIENT_DATA"
    elif float(delta) <= float(args.max_allowed_delta):
        status = "PASS_LOW_BACKFILL_DEPENDENCE"
    else:
        status = "FAIL_HIGH_BACKFILL_DEPENDENCE"

    out = {
        "schema": "logos_backfill_dependence_monitor_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "inputs": {
            "compare_json": str(args.compare_json).replace("\\", "/"),
            "max_allowed_delta": float(args.max_allowed_delta),
        },
        "metrics": {
            "pure_real_corr_candidate_ns": pure,
            "mixed_backfill_corr_candidate_ns": mixed,
            "delta_mixed_minus_pure": delta,
        },
        "status": status,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "status": status, "delta": delta}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

