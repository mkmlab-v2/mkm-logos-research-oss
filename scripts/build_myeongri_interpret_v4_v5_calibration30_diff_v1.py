#!/usr/bin/env python3
"""Compare v4 vs v5 insights on calibration30 row indices (B-track)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_V4 = ROOT / "reports/myeongri_interpret_v4_human_review_calibration30_latest.json"
DEFAULT_V5 = ROOT / "reports/myeongri_interpret_v5_human_review_calibration30_latest.json"
DEFAULT_OUT = ROOT / "reports/myeongri_interpret_v4_v5_calibration30_diff_latest.json"

_OVERCONF = re.compile(r"(정확한\s*해석|확실|확定적|모든\s*정보가\s*일치)")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v4-json", type=Path, default=DEFAULT_V4)
    ap.add_argument("--v5-json", type=Path, default=DEFAULT_V5)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.v4_json.is_file() or not args.v5_json.is_file():
        print(json.dumps({"ok": False, "error": "missing v4 or v5 calibration30"}))
        return 2

    v4 = {int(s["row_index"]): s for s in json.loads(args.v4_json.read_text(encoding="utf-8")).get("samples") or []}
    v5_doc = json.loads(args.v5_json.read_text(encoding="utf-8"))
    v5 = {int(s["row_index"]): s for s in v5_doc.get("samples") or []}

    rows_out = []
    improved_overconf = v4_only_needs = v5_pass_v4_needs = 0
    for ri in sorted(set(v4) & set(v5)):
        a, b = v4[ri], v5[ri]
        ins4 = str(a.get("mkm_advanced_insight") or "")
        ins5 = str(b.get("mkm_advanced_insight") or "")
        oc4 = bool(_OVERCONF.search(ins4))
        oc5 = bool(_OVERCONF.search(ins5))
        if oc4 and not oc5:
            improved_overconf += 1
        v4v = str(a.get("reviewer_verdict") or "")
        v5v = str(b.get("reviewer_verdict") or "")
        if v4v == "needs_edit" and v5v == "pass":
            v5_pass_v4_needs += 1
        if v4v == "needs_edit" and v5v != "pass":
            v4_only_needs += 1
        rows_out.append(
            {
                "row_index": ri,
                "insight_changed": ins4 != ins5,
                "overconfidence_v4": oc4,
                "overconfidence_v5": oc5,
                "verdict_v4": v4v,
                "verdict_v5": v5v,
                "coerced_v4": a.get("envelope_coerced_from_template"),
                "coerced_v5": b.get("envelope_coerced_from_template"),
            }
        )

    report = {
        "schema": "myeongri_interpret_v4_v5_calibration30_diff_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "rows_compared": len(rows_out),
        "insight_changed_count": sum(1 for r in rows_out if r["insight_changed"]),
        "overconfidence_cleared_count": improved_overconf,
        "v5_pass_v4_was_needs_edit_count": v5_pass_v4_needs,
        "v4_needs_edit_still_not_pass_v5_count": v4_only_needs,
        "v5_human_verdict_counts": v5_doc.get("human_verdict_counts"),
        "v5_calibration_gate_pass": v5_doc.get("calibration_gate_pass"),
        "rows": rows_out,
        "track_wall": {"operational_adapter_unchanged": "run_interpret_v4_variant_s100"},
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "rows": len(rows_out), "v5_pass_v4_needs": v5_pass_v4_needs}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
