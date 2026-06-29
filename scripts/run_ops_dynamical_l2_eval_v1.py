#!/usr/bin/env python3
"""Ops dynamical L2 — intervention equilibrium eval from JSONL [HYPO · B-track]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops_dynamical_bench_v1_lib import (  # noqa: E402
    DEFAULT_JSONL,
    DEFAULT_OUT,
    build_report,
    eval_l2_interventions,
    read_jsonl,
)

OUT = ROOT / "reports/ops_dynamical_l2_eval_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate ops dynamical L2 intervention pairs")
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--patch-bench-latest", action="store_true", default=True)
    parser.add_argument("--no-patch-bench-latest", dest="patch_bench_latest", action="store_false")
    args = parser.parse_args()

    rows = read_jsonl(args.jsonl)
    doc = eval_l2_interventions(rows)
    doc["jsonl_path"] = str(args.jsonl).replace("\\", "/")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.patch_bench_latest and doc["pairs_evaluated"] > 0:
        latest = build_report(fractal_level="L2_intervention")
        last = doc["pairs"][-1]
        latest["validation"] = {
            "observed_stage": last.get("stage_after"),
            "timing_error_minutes": None,
            "intervention_applied": True,
            "intervention_ok": last.get("intervention_ok"),
            "stress_delta": last.get("stress_delta"),
            "equilibrium_restored": last.get("equilibrium_restored"),
        }
        latest["fractal_level"] = "L2_intervention"
        DEFAULT_OUT.write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "pairs_evaluated": doc["pairs_evaluated"],
                "equilibrium_restore_rate": doc["metrics"]["equilibrium_restore_rate"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
