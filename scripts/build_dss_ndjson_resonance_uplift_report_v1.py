#!/usr/bin/env python3
"""Compact H-DSS1 uplift summary from biblical_resonance_research_production_ab JSON."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AB = ROOT / "reports/biblical_resonance_research_production_ab_latest.json"
DEFAULT_OUT = ROOT / "reports/dss_ndjson_resonance_uplift_latest.json"
AB_SCRIPT = ROOT / "scripts/build_biblical_resonance_research_production_ab_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _hyp_metrics(arm: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(arm, dict):
        return {}
    h = arm.get("hypothesis") if isinstance(arm.get("hypothesis"), dict) else {}
    return {
        "matched_rows": h.get("matched_rows"),
        "coverage_ratio": h.get("coverage_ratio"),
        "composite_score": h.get("composite_score"),
    }


def _delta(a: dict[str, Any], b: dict[str, Any], key: str) -> float | None:
    av, bv = a.get(key), b.get(key)
    if isinstance(av, (int, float)) and isinstance(bv, (int, float)):
        return round(float(bv) - float(av), 6)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ab-json", type=Path, default=DEFAULT_AB)
    ap.add_argument("--refresh-ab", action="store_true")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.refresh_ab:
        rc = subprocess.run([sys.executable, str(AB_SCRIPT)], cwd=str(ROOT), check=False).returncode
        if rc != 0:
            print(json.dumps({"ok": False, "error": "ab_refresh_failed"}), file=sys.stderr)
            return rc

    if not args.ab_json.is_file():
        print(json.dumps({"ok": False, "error": f"missing ab json: {args.ab_json}"}), file=sys.stderr)
        return 2

    ab = _load(args.ab_json)
    arms = ab.get("arms") if isinstance(ab.get("arms"), dict) else {}
    prod = _hyp_metrics(arms.get("production"))
    slice_h = _hyp_metrics(arms.get("research_slice"))
    prod_dss = _hyp_metrics(arms.get("production_plus_dss_context"))
    prod_ndjson_arm = arms.get("production_plus_ndjson_context")
    slice_ndjson_arm = arms.get("research_slice_plus_ndjson_context")
    prod_ndjson = _hyp_metrics(prod_ndjson_arm)
    slice_ndjson = _hyp_metrics(slice_ndjson_arm)

    payload = {
        "schema": "dss_ndjson_resonance_uplift_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "hypothesis_id": ab.get("hypothesis_id", "H-DSS1"),
        "source_ab_json": str(args.ab_json),
        "production": prod,
        "research_slice": slice_h,
        "production_plus_dss_context": prod_dss,
        "production_plus_ndjson_context": prod_ndjson,
        "research_slice_plus_ndjson_context": slice_ndjson,
        "delta_prod_plus_ndjson_minus_production": {
            "matched_rows": _delta(prod, prod_ndjson, "matched_rows"),
            "coverage_ratio": _delta(prod, prod_ndjson, "coverage_ratio"),
            "composite_score": _delta(prod, prod_ndjson, "composite_score"),
        },
        "delta_slice_plus_ndjson_minus_research_slice": {
            "matched_rows": _delta(slice_h, slice_ndjson, "matched_rows"),
            "coverage_ratio": _delta(slice_h, slice_ndjson, "coverage_ratio"),
            "composite_score": _delta(slice_h, slice_ndjson, "composite_score"),
        },
        "interpretation": {
            "status": "research_only_not_promotion_proof",
            "note": "NDJSON uplift is keyword-coverage observation only; smoke manifests may under/over-state vs real frontline.",
        },
        "track_a_promotion": "blocked",
        "live_trading_trigger": "forbidden",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output_json),
                "delta_prod_ndjson_composite": payload["delta_prod_plus_ndjson_minus_production"]["composite_score"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
