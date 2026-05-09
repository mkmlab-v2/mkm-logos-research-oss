#!/usr/bin/env python3
"""Sweep compare_backfill parameters to minimize backfill dependence delta."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "logos_backfill_delta_sweep_latest.json"


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "command": cmd,
        "returncode": cp.returncode,
        "stdout": cp.stdout.strip(),
        "stderr": cp.stderr.strip(),
    }


def _extract_delta(compare_json: Path) -> float | None:
    if not compare_json.exists():
        return None
    doc = json.loads(compare_json.read_text(encoding="utf-8"))
    v = doc.get("delta_mixed_minus_pure")
    if isinstance(v, (int, float)):
        return float(v)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep backfill compare settings for lowest delta.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-allowed-delta", type=float, default=0.15)
    ap.add_argument("--bins-candidates", type=str, default="4,5,6,7,8")
    ap.add_argument("--min-non-synth-candidates", type=str, default="4,6,8,10")
    ap.add_argument("--balanced-max-per-day-candidates", type=str, default="1,2,3")
    args = ap.parse_args()

    bins_list = [int(x) for x in str(args.bins_candidates).split(",") if str(x).strip()]
    min_list = [int(x) for x in str(args.min_non_synth_candidates).split(",") if str(x).strip()]
    max_per_day_list = [max(1, int(x)) for x in str(args.balanced_max_per_day_candidates).split(",") if str(x).strip()]

    compare_tmp = ART / "logos_temporal_holdout_compare_backfill_sweep_tmp.json"
    runs: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None

    for bins in bins_list:
        for min_non in min_list:
            for max_per_day in max_per_day_list:
                rec = _run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "run_logos_temporal_holdout_compare_backfill_v1.py"),
                        "--bins",
                        str(bins),
                        "--min-non-synth-per-bin",
                        str(min_non),
                        "--balanced-max-per-day",
                        str(max_per_day),
                        "--output-json",
                        str(compare_tmp),
                    ]
                )
                delta = _extract_delta(compare_tmp) if rec["returncode"] == 0 else None
                item = {
                    "bins": bins,
                    "min_non_synth_per_bin": min_non,
                    "balanced_max_per_day": max_per_day,
                    "returncode": rec["returncode"],
                    "delta_mixed_minus_pure": delta,
                }
                runs.append(item)
                if delta is None:
                    continue
                if best is None or float(delta) < float(best["delta_mixed_minus_pure"]):
                    best = item

    pass_found = bool(best is not None and best.get("delta_mixed_minus_pure") is not None and float(best["delta_mixed_minus_pure"]) <= float(args.max_allowed_delta))
    out = {
        "schema": "logos_backfill_delta_sweep_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "max_allowed_delta": float(args.max_allowed_delta),
        "candidate_grid": {
            "bins": bins_list,
            "min_non_synth_per_bin": min_list,
            "balanced_max_per_day": max_per_day_list,
        },
        "run_count": len(runs),
        "best": best,
        "pass_found": pass_found,
        "runs": runs,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "best_delta": None if best is None else best.get("delta_mixed_minus_pure"),
                "pass_found": pass_found,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

