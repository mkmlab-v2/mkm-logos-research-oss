#!/usr/bin/env python3
"""A2A dialogue under two routing profiles (track_a_promoted vs b_track_domain_relax)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_dialogue_routing_compare_latest.json"
PROFILES = ("track_a_promoted", "b_track_domain_relax")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_compare(*, turns: int = 4, scenario: str = "health") -> dict[str, Any]:
    from scripts.run_mkm_inter_agent_dialogue_mock_v1 import run_dialogue

    runs: list[dict[str, Any]] = []
    for profile in PROFILES:
        doc = run_dialogue(turns=turns, scenario=scenario, routing_profile=profile)
        savings: list[float] = []
        for row in doc.get("transcript") or []:
            compress = row.get("compress") or {}
            m = compress.get("compression_metrics")
            if isinstance(m, dict) and m.get("savings_ratio") is not None:
                savings.append(float(m["savings_ratio"]))
        runs.append(
            {
                "routing_profile": profile,
                "all_compress_ok": doc.get("all_compress_ok"),
                "all_expand_ok": doc.get("all_expand_ok"),
                "avg_savings_ratio": (sum(savings) / len(savings)) if savings else None,
                "transcript_turn_count": len(doc.get("transcript") or []),
            }
        )
    delta = None
    if len(runs) == 2 and runs[0].get("avg_savings_ratio") is not None and runs[1].get("avg_savings_ratio") is not None:
        delta = round(float(runs[1]["avg_savings_ratio"]) - float(runs[0]["avg_savings_ratio"]), 6)
    return {
        "schema": "mkm_inter_agent_dialogue_routing_compare_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "hypothesis_tier": "B",
        "scenario": scenario,
        "boundary_ack": (
            "Dialogue-turn avg savings only — not Track A 40-case bench. "
            "b_track_domain_relax is research_only."
        ),
        "profiles_compared": list(PROFILES),
        "runs": runs,
        "avg_savings_delta_b_track_minus_track_a": delta,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--scenario", choices=("trading", "health"), default="health")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_compare(turns=max(2, args.turns), scenario=args.scenario)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
