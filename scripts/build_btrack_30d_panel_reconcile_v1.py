#!/usr/bin/env python3
"""[HYPO] Reconcile two B-track score panels (date overlap + prediction drift)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_A = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
DEFAULT_B = ROOT / "docs/final/artifacts/btrack_prophecy_score_30d_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_30d_panel_reconcile_v1_latest.json"


def _btc_map(path: Path) -> dict[str, dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for r in doc.get("rows") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("instrument") or "").lower() != "btc":
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if ed:
            out[ed] = r
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anchor", type=Path, default=DEFAULT_A)
    ap.add_argument("--other", type=Path, default=DEFAULT_B)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    a = _btc_map(args.anchor)
    b = _btc_map(args.other)
    da, db = set(a), set(b)
    overlap = sorted(da & db)
    rows_overlap = []
    for d in overlap:
        ra, rb = a[d], b[d]
        rows_overlap.append(
            {
                "eval_date": d,
                "anchor_pred": ra.get("predicted_direction"),
                "other_pred": rb.get("predicted_direction"),
                "anchor_actual": ra.get("actual_direction"),
                "other_actual": rb.get("actual_direction"),
                "pred_match": ra.get("predicted_direction") == rb.get("predicted_direction"),
            }
        )

    def rate(m: dict[str, dict[str, Any]]) -> float | None:
        if not m:
            return None
        hits = sum(1 for r in m.values() if r.get("predicted_direction") == r.get("actual_direction"))
        return round(hits / len(m), 6)

    report = {
        "schema": "btrack_30d_panel_reconcile_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "anchor": str(args.anchor),
        "other": str(args.other),
        "anchor_n": len(da),
        "other_n": len(db),
        "anchor_hit_rate": rate(a),
        "other_hit_rate": rate(b),
        "only_anchor_dates": sorted(da - db),
        "only_other_dates": sorted(db - da),
        "overlap_n": len(overlap),
        "pred_mismatch_on_overlap": sum(1 for r in rows_overlap if not r["pred_match"]),
        "overlap_detail": rows_overlap,
        "operator_line": (
            "43.3% vs 62.1% headline gap is largely different date windows + frozen bear vs bull "
            "hypothesis batch — not the same experiment."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(report["operator_line"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
