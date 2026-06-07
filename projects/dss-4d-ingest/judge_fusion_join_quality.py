#!/usr/bin/env python3
"""Fusion join quality gate: DSS × apocrypha NDJSON overlap metadata only.

research_only · [HYPO] · NON_GATING.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_ndjson(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        obj = json.loads(raw)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _work_key(row: dict[str, Any]) -> str:
    return str(row.get("work") or row.get("work_id") or "").strip().lower()


def _overlap_keys(rows: list[dict[str, Any]]) -> set[str]:
    return {_work_key(r) for r in rows if _work_key(r)}


def _tier_script_keys(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for r in rows:
        script = str(r.get("script") or "")
        tier = str(r.get("lineage_tier") or "")
        if script and tier:
            out.add((script, tier))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dss-ndjson", type=Path, required=True)
    ap.add_argument("--apocrypha-ndjson", type=Path, required=True)
    ap.add_argument("--min-overlap-tokens", type=int, default=5)
    ap.add_argument("--min-overlap-ratio-dss", type=float, default=0.005)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    if not args.dss_ndjson.is_file():
        print(json.dumps({"ok": False, "error": f"missing {args.dss_ndjson}"}), file=sys.stderr)
        return 2
    if not args.apocrypha_ndjson.is_file():
        print(json.dumps({"ok": False, "error": f"missing {args.apocrypha_ndjson}"}), file=sys.stderr)
        return 2

    dss_rows = _load_ndjson(args.dss_ndjson)
    apo_rows = _load_ndjson(args.apocrypha_ndjson)
    dss_works = _overlap_keys(dss_rows)
    apo_works = _overlap_keys(apo_rows)
    work_overlap = dss_works & apo_works

    dss_tier = _tier_script_keys(dss_rows)
    apo_tier = _tier_script_keys(apo_rows)
    tier_overlap = dss_tier & apo_tier

    overlap_token_estimate = sum(1 for r in dss_rows if _work_key(r) in work_overlap)
    dss_count = len(dss_rows) or 1
    overlap_ratio = overlap_token_estimate / dss_count

    status = "PASS"
    fail_reasons: list[str] = []
    if overlap_token_estimate < args.min_overlap_tokens:
        status = "FAIL"
        fail_reasons.append("overlap_token_estimate_below_min")
    if overlap_ratio < args.min_overlap_ratio_dss:
        status = "FAIL"
        fail_reasons.append("overlap_ratio_dss_below_min")

    payload = {
        "schema": "fusion_join_quality_v1",
        "status": status,
        "join_profile": "work_label_bridge",
        "gate_semantics": "metadata_only_non_gating",
        "dss_ndjson": str(args.dss_ndjson),
        "apocrypha_ndjson": str(args.apocrypha_ndjson),
        "dss_record_count": len(dss_rows),
        "apocrypha_record_count": len(apo_rows),
        "dss_work_label_count": len(dss_works),
        "apocrypha_work_label_count": len(apo_works),
        "dss_work_label_samples": sorted(dss_works)[:20],
        "apocrypha_work_label_samples": sorted(apo_works)[:20],
        "work_overlap_count": len(work_overlap),
        "work_overlap_samples": sorted(work_overlap)[:20],
        "tier_script_overlap_count": len(tier_overlap),
        "overlap_token_estimate": overlap_token_estimate,
        "overlap_ratio_dss": round(overlap_ratio, 6),
        "weight_overlap_count": len(work_overlap),
        "numeric_overlap_count": len(tier_overlap),
        "fail_reasons": fail_reasons,
        "thresholds": {
            "min_overlap_tokens": args.min_overlap_tokens,
            "min_overlap_ratio_dss": args.min_overlap_ratio_dss,
        },
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"status={status}")
    print(f"report={args.out}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
