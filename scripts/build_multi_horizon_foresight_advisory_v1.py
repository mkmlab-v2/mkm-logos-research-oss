#!/usr/bin/env python3
"""Build Field→Lens→Conflict advisory sample for MHFV [HYPO] — no order trigger."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/multi_horizon_foresight_advisory_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
        return o if isinstance(o, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    closure = _load(ROOT / "reports/btrack_prophecy_research_closure_v1_latest.json")
    compare = _load(ROOT / "reports/chain_proposal_reproduction_compare_v1_latest.json")

    lens_mean = None
    inst_mean = None
    if compare and isinstance(compare.get("rows"), list):
        for row in compare["rows"]:
            if row.get("test_policy") == "ensemble-top3":
                lens_mean = row.get("lens_mean_test_accuracy")
                inst_mean = row.get("instrument_mean_test_accuracy")

    field_regime = "GATE_FAILED_HOLD"
    if closure:
        field_regime = closure.get("track_a_status", field_regime)

    doc = {
        "schema": "multi_horizon_foresight_advisory_v1",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "field": {
            "regime_id": field_regime,
            "note": "1차 실물 regime_map + ops gates; not a lens name",
        },
        "lenses": {
            "sasang": {
                "role": "단기 강도",
                "signal": "instrument_hypo_uplift_observed",
                "metric": inst_mean,
                "track": "b_track_hypo",
            },
            "myeongni": {
                "role": "중기 방향",
                "signal": "profile_deterministic_only",
                "market_auto_substitute": False,
                "track": "deterministic_profile",
            },
            "logos": {
                "role": "거시 게이트",
                "tag": "[NON_GATING]",
                "signal": "macro_scenario_advisory",
                "track": "non_gating_advisory",
            },
        },
        "conflict": {
            "description": "instrument_pass_vs_lens_sub_gate",
            "lens_mean_test_accuracy": lens_mean,
            "instrument_mean_test_accuracy": inst_mean,
            "combined_strict_pass": False,
        },
        "final_action": "HOLD",
        "final_action_allowed_values": ["HOLD", "WATCH", "REDUCE"],
        "live_order_trigger": False,
        "track_a_auto_merge": False,
    }
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out.resolve()} final_action={doc['final_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
