#!/usr/bin/env python3
"""[HYPO] Neutral-abstain miss cohort: attribution + actual direction (30d BTC)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MISS = ROOT / "reports/btrack_headline_miss_report_v1_latest.json"
DEFAULT_PER_DATE = ROOT / "reports/btrack_ensemble_per_date_directions_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_neutral_abstain_cohort_report_v1_latest.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(miss_doc: dict[str, Any], per_date_doc: dict[str, Any]) -> dict[str, Any]:
    by_date = {
        str(r.get("eval_date"))[:10]: r
        for r in (per_date_doc.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
    }
    cohort: list[dict[str, Any]] = []
    for m in miss_doc.get("misses") or []:
        if not isinstance(m, dict) or m.get("miss_kind") != "neutral_abstain_miss":
            continue
        ed = str(m.get("eval_date"))[:10]
        row = by_date.get(ed) or {}
        gate = row.get("low_confidence_direction_gate") if isinstance(row.get("low_confidence_direction_gate"), dict) else {}
        cohort.append(
            {
                "eval_date": ed,
                "predicted_direction": m.get("predicted_direction"),
                "actual_direction": m.get("actual_direction"),
                "preliminary_direction": row.get("preliminary_direction"),
                "weighted_score": row.get("weighted_score"),
                "confidence": row.get("confidence"),
                "low_conf_gate_applied": bool(gate.get("applied")),
                "would_directional_if_no_gate": row.get("preliminary_direction"),
                "note": (
                    "Lowering min_conf only helps if preliminary was directional and gate blocked; "
                    "margin-band neutrals need margin/ensemble change."
                ),
            }
        )
    gate_blocked = sum(1 for c in cohort if c.get("low_conf_gate_applied"))
    return {
        "schema": "btrack_neutral_abstain_cohort_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "n_neutral_abstain_misses": len(cohort),
        "summary": {
            "low_conf_gate_blocked": gate_blocked,
            "recommendation": (
                "Do not lower min_conf below 0.18 without holdout; "
                f"{gate_blocked}/{len(cohort)} neutral misses had gate applied on preliminary directional."
            ),
        },
        "cohort_days": cohort,
        "operator_line": (
            f"- [MKM-NEUTRAL-COHORT] {len(cohort)} neutral_abstain misses; "
            f"low_conf_gate={gate_blocked} — hold min_conf=0.18; fix margin/ensemble not abstain"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--miss-report", type=Path, default=DEFAULT_MISS)
    ap.add_argument("--per-date-json", type=Path, default=DEFAULT_PER_DATE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.miss_report.is_file() or not args.per_date_json.is_file():
        print("Missing miss or per-date JSON.", file=sys.stderr)
        return 2
    report = build_report(_load(args.miss_report), _load(args.per_date_json))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(report["operator_line"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
