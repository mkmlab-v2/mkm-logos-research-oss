#!/usr/bin/env python3
"""Merge comp_en_tech_semantic_gpu_poc shard JSONs (multi-host / research_only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_local_v1_latest.json"
FROZEN_CPU = ROOT / "reports/constitution/btrack_pilot/comp_en_tech_oov_coverage_from_cpu_freeze_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("shard_globs", nargs="+", help="Paths or glob patterns to shard JSON files")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    paths: list[Path] = []
    for pat in args.shard_globs:
        p = Path(pat)
        if p.is_file():
            paths.append(p.resolve())
        else:
            paths.extend(sorted(ROOT.glob(pat)))

    if not paths:
        print("error: no shard files", file=sys.stderr)
        return 1

    shards: list[dict[str, Any]] = []
    for path in paths:
        shards.append(json.loads(path.read_text(encoding="utf-8-sig")))

    per_case: list[dict[str, Any]] = []
    seen: set[str] = set()
    for doc in shards:
        for row in doc.get("per_case") or []:
            cid = str(row.get("case_id") or "")
            if cid in seen:
                continue
            seen.add(cid)
            per_case.append(row)
    per_case.sort(key=lambda r: str(r.get("case_id") or ""))

    jaccards = [float(r["metrics"]["avg_reconstruction_fidelity_jaccard"]) for r in per_case]
    savings = [float(r["metrics"]["global_token_saving_rate"]) for r in per_case]
    agg = {
        "case_count": len(per_case),
        "jaccard_mean": round(sum(jaccards) / len(jaccards), 6) if jaccards else 0.0,
        "jaccard_min": round(min(jaccards), 6) if jaccards else 0.0,
        "saving_mean": round(sum(savings) / len(savings), 6) if savings else 0.0,
        "below_0_85_count": sum(1 for j in jaccards if j < 0.85),
    }

    frozen_ref: dict[str, Any] = {}
    if FROZEN_CPU.is_file():
        fdoc = json.loads(FROZEN_CPU.read_text(encoding="utf-8-sig"))
        frozen_ref = {
            "jaccard_mean_frozen_literal": fdoc.get("aggregate", {}).get("jaccard_mean_frozen_literal"),
            "jaccard_min_frozen_literal": fdoc.get("aggregate", {}).get("jaccard_min_frozen_literal"),
        }
    beat_frozen = (
        agg["jaccard_min"] > 0.758 and agg["jaccard_mean"] > 0.769 if frozen_ref else None
    )

    base = shards[0]
    out_doc = {
        "schema": "comp_en_tech_semantic_gpu_poc_local_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "merged_from": [str(p.relative_to(ROOT)).replace("\\", "/") for p in paths],
        "merge_shard_hosts": [s.get("host_label") for s in shards],
        "lane_id": base.get("lane_id"),
        "compression_profile": base.get("compression_profile"),
        "must_keep_patch_json": base.get("must_keep_patch_json"),
        "must_keep_token_count": base.get("must_keep_token_count"),
        "aggregate": agg,
        "frozen_cpu_cross_check": frozen_ref,
        "beat_frozen_cpu_literal_research_only": beat_frozen,
        "track_a_active_written": False,
        "per_case": per_case,
        "p3_lab_gate_note": base.get("p3_lab_gate_note"),
    }
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"), "case_count": len(per_case)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
