#!/usr/bin/env python3
"""Consolidate DSS B-track research artifacts into one handoff JSON with profile guidance."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPARE = ROOT / "reports/dss_ndjson_profile_surface_compare_latest.json"
DEFAULT_EXT3_AB = ROOT / "reports/biblical_resonance_isolated_production_ab_ext3_only_latest.json"
DEFAULT_DEFAULT_AB = ROOT / "reports/biblical_resonance_isolated_production_ab_latest.json"
DEFAULT_SLICE_DECOUPLED = ROOT / "reports/biblical_resonance_isolated_production_ab_slice_decoupled_latest.json"
DEFAULT_PIN = ROOT / "reports/dss_authority_pin_policy_research_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/dss_research_lane_handoff_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _efficiency(surface_rows: int | None, delta_matched: float | None) -> float | None:
    if not surface_rows or surface_rows <= 0 or delta_matched is None:
        return None
    return round(float(delta_matched) / float(surface_rows), 6)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile-compare-json", type=Path, default=DEFAULT_COMPARE)
    ap.add_argument("--default-isolated-ab-json", type=Path, default=DEFAULT_DEFAULT_AB)
    ap.add_argument("--ext3-isolated-ab-json", type=Path, default=DEFAULT_EXT3_AB)
    ap.add_argument("--slice-decoupled-ab-json", type=Path, default=DEFAULT_SLICE_DECOUPLED)
    ap.add_argument("--pin-policy-json", type=Path, default=DEFAULT_PIN)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    compare = _load(args.profile_compare_json)
    profiles = compare.get("profiles") if isinstance(compare.get("profiles"), dict) else {}
    default_p = profiles.get("default_3file") if isinstance(profiles.get("default_3file"), dict) else {}
    ext3_p = profiles.get("ext3_only") if isinstance(profiles.get("ext3_only"), dict) else {}

    default_delta = default_p.get("delta_repair_minus_raw") if isinstance(default_p.get("delta_repair_minus_raw"), dict) else {}
    ext3_delta = ext3_p.get("delta_repair_minus_raw") if isinstance(ext3_p.get("delta_repair_minus_raw"), dict) else {}

    default_eff = _efficiency(default_p.get("surface_rows"), default_delta.get("matched_rows"))
    ext3_eff = _efficiency(ext3_p.get("surface_rows"), ext3_delta.get("matched_rows"))

    recommendation = "ext3_only"
    if default_eff is not None and ext3_eff is not None and default_eff > ext3_eff:
        recommendation = "default_3file_max_coverage"
    note = (
        "ext3_only: Hebrew-priority pin-aligned, fewer metadata rows, cleaner operator readout."
        if recommendation == "ext3_only"
        else "default_3file: higher matched-per-surface-row efficiency in isolated AB."
    )

    slice_dec = _load(args.slice_decoupled_ab_json)
    slice_iso = slice_dec.get("isolation") if isinstance(slice_dec.get("isolation"), dict) else {}

    payload = {
        "schema": "dss_research_lane_handoff_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "profiles": {
            "default_3file": {
                "surface_rows": default_p.get("surface_rows"),
                "delta_matched": default_delta.get("matched_rows"),
                "delta_composite": default_delta.get("alignment_pass_rate_delta_repair_v2_minus_raw"),
                "matched_per_surface_row": default_eff,
            },
            "ext3_only": {
                "surface_rows": ext3_p.get("surface_rows"),
                "delta_matched": ext3_delta.get("matched_rows"),
                "delta_composite": ext3_delta.get("alignment_pass_rate_delta_repair_v2_minus_raw"),
                "matched_per_surface_row": ext3_eff,
            },
        },
        "slice_decoupled_isolation": slice_iso,
        "slice_decoupling_policy": {
            "research_slice_jsonl": "docs/final/artifacts/news_observation_v1_biblical_history_research_slice_decoupled_latest.jsonl",
            "flags": "skip_ndjson_context + skip_korea_context",
            "rationale": "Korea/health feeds duplicate prod ledger text_sha256; omit for zero-overlap isolated AB.",
        },
        "pin_policy": _load(args.pin_policy_json).get("resolution"),
        "guidance": {
            "recommended_ndjson_profile": recommendation,
            "note": note,
            "weekly_ssot": "default_3file remains AB SSOT; ext3_only for Hebrew-priority reports",
        },
        "artifacts": {
            "profile_compare": str(args.profile_compare_json),
            "default_isolated_ab": str(args.default_isolated_ab_json),
            "ext3_isolated_ab": str(args.ext3_isolated_ab_json),
            "slice_decoupled_ab": str(args.slice_decoupled_ab_json),
        },
        "track_a_promotion": "blocked",
        "live_trading_trigger": "forbidden",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "recommended": recommendation, "output": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
