#!/usr/bin/env python3
"""Aggregate matrix sweep rows excluding lanes (e.g. chunk_table) — no re-eval."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_v1.json"
DEFAULT_OUT = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_290_subset_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _agg(rows: list[dict], profile: str, key: str) -> dict[str, float]:
    vals = [
        float(r[profile][key])
        for r in rows
        if r.get(profile, {}).get(key) is not None
    ]
    if not vals:
        return {}
    return {"mean": sum(vals) / len(vals), "min": min(vals), "max": max(vals)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--exclude-lane-id",
        action="append",
        default=["ijeoma_chunk_table_v1", "ijeoma_chunk_cjk_hypo_v1"],
        help="Repeatable; default excludes both chunk lanes (290 operational KPI).",
    )
    args = ap.parse_args()

    in_path = (ROOT / args.in_json).resolve() if not args.in_json.is_absolute() else args.in_json
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    if not in_path.is_file():
        print(json.dumps({"error": "missing", "path": str(in_path)}, ensure_ascii=False))
        return 2

    doc = json.loads(in_path.read_text(encoding="utf-8"))
    exclude = set(args.exclude_lane_id or [])
    rows = [r for r in doc.get("rows") or [] if str(r.get("lane_id") or "") not in exclude]

    out = {
        "schema": "comp_universal_bench_matrix_sweep_subset_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "source_sweep": str(in_path.relative_to(ROOT)).replace("\\", "/"),
        "excluded_lane_ids": sorted(exclude),
        "case_count": len(rows),
        "profiles": {
            "economy": _agg(rows, "economy", "global_token_saving_rate"),
            "economy_plus_wire": _agg(rows, "economy_plus_wire", "global_token_saving_rate"),
        },
        "jaccard_aggregate": {
            "economy": _agg(rows, "economy", "avg_reconstruction_fidelity_jaccard"),
            "economy_plus_wire": _agg(rows, "economy_plus_wire", "avg_reconstruction_fidelity_jaccard"),
        },
        "headline": {},
        "do_not_promote": doc.get("do_not_promote") or [
            "Not MS/Golden headline; subset of universal matrix sweep only."
        ],
    }
    es = out["profiles"]["economy"].get("mean")
    if es is not None:
        out["headline"]["economy_mean_saving_pct"] = round(es * 100, 2)
    ej = out["jaccard_aggregate"]["economy"].get("mean")
    if ej is not None:
        out["headline"]["economy_mean_jaccard"] = round(ej, 4)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "case_count": len(rows),
                "headline": out["headline"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
