#!/usr/bin/env python3
"""Weighted wire AB summary excluding lanes (default: ijeoma_chunk) — B-track only."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_wire_ab_summary_v1.json"
DEFAULT_OUT = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_wire_ab_summary_290_subset_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _wmean(rows: list[dict], field: str) -> float | None:
    num = 0.0
    den = 0
    for r in rows:
        v = r.get(field)
        n = int(r.get("case_count") or 0)
        if v is None or n <= 0:
            continue
        num += float(v) * n
        den += n
    return round(num / den, 4) if den else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--exclude-lane-key",
        action="append",
        default=["ijeoma_chunk"],
    )
    args = ap.parse_args()

    in_path = (ROOT / args.in_json).resolve() if not args.in_json.is_absolute() else args.in_json
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    if not in_path.is_file():
        print(json.dumps({"error": "missing", "path": str(in_path)}, ensure_ascii=False))
        return 2

    doc = json.loads(in_path.read_text(encoding="utf-8"))
    exclude = set(args.exclude_lane_key or [])
    rows = [r for r in doc.get("rows") or [] if str(r.get("lane_key") or "") not in exclude]
    case_count = sum(int(r.get("case_count") or 0) for r in rows)

    out = {
        "schema": "comp_universal_bench_matrix_wire_ab_summary_290_subset_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "source": str(in_path.relative_to(ROOT)).replace("\\", "/"),
        "excluded_lane_keys": sorted(exclude),
        "case_count": case_count,
        "lane_count": len(rows),
        "rows": rows,
        "weighted_headline": {
            "delta_jaccard_pp": _wmean(rows, "delta_jaccard_pp"),
            "delta_saving_pp": _wmean(rows, "delta_saving_pp"),
            "bridge_boost_cases": sum(int(r.get("bridge_boost_cases") or 0) for r in rows),
        },
        "do_not_promote": doc.get("do_not_promote")
        or [
            "Not MS Golden 47.5%; not Track A active KPI",
            "Chunk lane excluded from operational wire AB mean",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "case_count": case_count,
                "weighted_headline": out["weighted_headline"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
