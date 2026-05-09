#!/usr/bin/env python3
"""Build S1 shadow comparator: baseline vs flip-candidate simulation."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_WEEKLY = ART / "lens_penalty_shadow_weekly_report_latest.json"
DEFAULT_SWEEP = ART / "lens_penalty_direction_sensitivity_sweep_latest.json"
DEFAULT_ALLOWLIST = ART / "lens_penalty_s1_shadow_allowlist_v1.json"
DEFAULT_OUT = ART / "lens_penalty_s1_shadow_comparator_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weekly-json", type=Path, default=DEFAULT_WEEKLY)
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--allowlist-json", type=Path, default=DEFAULT_ALLOWLIST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    weekly = _read_json(args.weekly_json)
    sweep = _read_json(args.sweep_json)
    allowlist_doc = _read_json(args.allowlist_json)
    allowlist_enabled = bool(allowlist_doc.get("enabled", True))
    allowed_set = {
        str(x).strip()
        for x in (allowlist_doc.get("allowed_flip_lenses") if isinstance(allowlist_doc.get("allowed_flip_lenses"), list) else [])
        if str(x).strip()
    }

    per_lens_weekly = weekly.get("per_lens") if isinstance(weekly.get("per_lens"), list) else []
    baseline_total_events = int((weekly.get("summary") or {}).get("total_events") or 0)
    baseline_total_fail = int((weekly.get("summary") or {}).get("total_fail") or 0)
    strict_max_fail_rate = float((weekly.get("summary") or {}).get("strict_max_fail_rate") or 0.45)

    sweep_per_lens = sweep.get("per_lens") if isinstance(sweep.get("per_lens"), list) else []
    sweep_map: dict[str, dict[str, Any]] = {}
    for row in sweep_per_lens:
        if not isinstance(row, dict):
            continue
        lens_id = str(row.get("lens_id") or "").strip()
        if lens_id:
            sweep_map[lens_id] = row

    simulated_total_fail = 0
    comparator_rows: list[dict[str, Any]] = []
    for row in per_lens_weekly:
        if not isinstance(row, dict):
            continue
        lens_id = str(row.get("lens_id") or "").strip()
        events = int(row.get("events") or 0)
        base_fail = int(row.get("fail_count") or 0)
        pick = sweep_map.get(lens_id, {})
        recommend_flip = bool(pick.get("recommend_flip_shadow_candidate"))
        if allowlist_enabled:
            recommend_flip = recommend_flip and (lens_id in allowed_set)
        flip_sim = pick.get("flip_simulation") if isinstance(pick.get("flip_simulation"), dict) else {}
        if recommend_flip and isinstance(flip_sim, dict) and ("fail_count" in flip_sim):
            sim_fail = int(flip_sim.get("fail_count") or 0)
        else:
            sim_fail = base_fail
        simulated_total_fail += sim_fail
        comparator_rows.append(
            {
                "lens_id": lens_id,
                "events": events,
                "baseline_fail_count": base_fail,
                "simulated_fail_count": sim_fail,
                "recommend_flip_shadow_candidate": recommend_flip,
            }
        )

    baseline_fail_rate = round((baseline_total_fail / baseline_total_events), 6) if baseline_total_events > 0 else 0.0
    simulated_fail_rate = round((simulated_total_fail / baseline_total_events), 6) if baseline_total_events > 0 else 0.0
    baseline_gap = round(baseline_fail_rate - strict_max_fail_rate, 6)
    simulated_gap = round(simulated_fail_rate - strict_max_fail_rate, 6)

    out = {
        "schema": "lens_penalty_s1_shadow_comparator_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "weekly_json": str(args.weekly_json.resolve()).replace("\\", "/"),
            "sweep_json": str(args.sweep_json.resolve()).replace("\\", "/"),
            "allowlist_json": str(args.allowlist_json.resolve()).replace("\\", "/"),
        },
        "summary": {
            "events": baseline_total_events,
            "strict_max_fail_rate": strict_max_fail_rate,
            "baseline_fail_rate": baseline_fail_rate,
            "baseline_strict_gap": baseline_gap,
            "simulated_fail_rate": simulated_fail_rate,
            "simulated_strict_gap": simulated_gap,
            "delta_fail_rate": round(simulated_fail_rate - baseline_fail_rate, 6),
            "delta_strict_gap": round(simulated_gap - baseline_gap, 6),
            "flip_candidates": sum(1 for x in comparator_rows if bool(x["recommend_flip_shadow_candidate"])),
            "allowlist_enabled": allowlist_enabled,
            "allowlist_size": len(allowed_set),
        },
        "per_lens": comparator_rows,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"baseline_gap={baseline_gap}; simulated_gap={simulated_gap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
