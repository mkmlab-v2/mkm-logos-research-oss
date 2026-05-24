#!/usr/bin/env python3
"""Run mixed vs homogeneous Golden 40 expansion dry-runs and emit compare summary."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DRYRUN = ROOT / "scripts/run_golden40_expansion_dryrun_v1.py"
MANIFEST_BUILDER = ROOT / "scripts/build_golden40_homogeneous_expansion_manifest_v1.py"
DEFAULT_OUT = ROOT / "reports/golden_40_expansion_pool_compare_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _tier_summary(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tier in doc.get("tiers") or []:
        agg = tier.get("aggregate_metrics") or {}
        rows.append(
            {
                "target": tier.get("target_case_count"),
                "actual": tier.get("actual_case_count"),
                "saving": agg.get("global_token_saving_rate"),
                "jaccard": agg.get("avg_reconstruction_fidelity_jaccard"),
                "floor_ok": tier.get("floor_regression_ok"),
                "golden_core_jaccard": (tier.get("golden_core_only_metrics") or {}).get(
                    "avg_reconstruction_fidelity_jaccard"
                ),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare Golden 40 expansion pool modes.")
    ap.add_argument("--target-counts", default="40,80,120")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    subprocess.run([sys.executable, str(MANIFEST_BUILDER)], cwd=ROOT, check=True)

    modes = {
        "mixed_matrix": ROOT / "reports/golden_40_expansion_dryrun_mixed_v1_latest.json",
        "homogeneous_sasang_ko": ROOT / "reports/golden_40_expansion_dryrun_homogeneous_v1_latest.json",
        "homogeneous_logos_verse": ROOT / "reports/golden_40_expansion_dryrun_logos_verse_v1_latest.json",
        "homogeneous_en_ops": ROOT / "reports/golden_40_expansion_dryrun_en_ops_v1_latest.json",
        "homogeneous_full": ROOT / "reports/golden_40_expansion_dryrun_homogeneous_full_v1_latest.json",
    }
    exits: dict[str, int] = {}
    for mode, out_path in modes.items():
        cmd = [
            sys.executable,
            str(DRYRUN),
            "--pool-mode",
            mode,
            "--target-counts",
            args.target_counts,
            "--out-json",
            str(out_path),
        ]
        if args.plan_only:
            cmd.append("--plan-only")
        proc = subprocess.run(cmd, cwd=ROOT)
        exits[mode] = proc.returncode

    docs = {mode: _load(path) for mode, path in modes.items() if path.is_file()}
    compare: dict[str, Any] = {
        "schema": "golden_40_expansion_pool_compare_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "target_counts": args.target_counts,
        "plan_only": bool(args.plan_only),
        "exit_codes": exits,
        "pools": {
            mode: {
                "artifact": str(path.relative_to(ROOT)).replace("\\", "/"),
                "max_available": doc.get("tiers", [{}])[-1].get("max_available_in_pool") if doc.get("tiers") else None,
                "expansion_dilution": (doc.get("summary") or {}).get("expansion_dilution_observed"),
                "mixed_domain_dilution": (doc.get("summary") or {}).get("mixed_domain_dilution_observed"),
                "tier_summary": _tier_summary(doc),
            }
            for mode, doc in docs.items()
            for path in [modes[mode]]
        },
        "promotion_recommendation": "HOLD",
        "news_readiness": False,
    }

    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(compare, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    worst = max(exits.values()) if exits else 0
    return 0 if worst == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
