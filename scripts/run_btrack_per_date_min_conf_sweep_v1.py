#!/usr/bin/env python3
"""Sweep min_direction_confidence on existing per-date direction rows (B-track)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_per_date_min_conf_sweep_v1_latest.json"
APPLY = ROOT / "scripts/apply_btrack_min_conf_to_per_date_directions_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _counts(doc: dict[str, Any]) -> dict[str, int]:
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    c = {"bull": 0, "bear": 0, "neutral": 0, "abstain": 0, "other": 0}
    for r in rows:
        if not isinstance(r, dict):
            continue
        d = str(r.get("predicted_direction") or "").strip().lower()
        if d in c:
            c[d] += 1
        else:
            c["other"] += 1
    c["total"] = sum(c.values())
    c["directional_calls"] = c["bull"] + c["bear"]
    return c


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--grid",
        default="0.08,0.12,0.15,0.18,0.25,0.35",
        help="Comma-separated min_direction_confidence values.",
    )
    ap.add_argument("--work-dir", type=Path, default=ROOT / "reports/btrack_per_date_min_conf_sweep_v1")
    args = ap.parse_args()
    if not args.input.is_file():
        print(f"Missing: {args.input}", file=sys.stderr)
        return 2

    grid = [float(x.strip()) for x in str(args.grid).split(",") if x.strip()]
    args.work_dir.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict[str, Any]] = []
    py = sys.executable

    for thresh in grid:
        slug = str(thresh).replace(".", "p")
        out_path = args.work_dir / f"directions_minconf_{slug}.json"
        cmd = [
            py,
            str(APPLY),
            "--input",
            str(args.input),
            "--output",
            str(out_path),
            "--min-direction-confidence",
            str(thresh),
        ]
        rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
        doc = json.loads(out_path.read_text(encoding="utf-8")) if out_path.is_file() else {}
        counts = _counts(doc)
        gated_n = (doc.get("gate_meta") or {}).get("rows_gated_to_neutral")
        rows_out.append(
            {
                "min_direction_confidence": thresh,
                "exit_code": rc,
                "output_json": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "direction_counts": counts,
                "rows_gated_to_neutral": gated_n,
                "call_rate_directional": round(
                    counts["directional_calls"] / counts["total"], 6
                )
                if counts.get("total")
                else None,
            }
        )
        print(
            f"thresh={thresh} gated={gated_n} directional={counts['directional_calls']}/{counts['total']}",
            file=sys.stderr,
        )

    doc_out = {
        "schema": "btrack_per_date_min_conf_sweep_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "input": str(args.input.relative_to(ROOT)).replace("\\", "/"),
        "rows": rows_out,
        "note": "Post-hoc gate on existing per-date rows; does not rebuild ensemble lenses.",
    }
    args.output.write_text(json.dumps(doc_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0 if all(int(r["exit_code"]) == 0 for r in rows_out) else 1


if __name__ == "__main__":
    raise SystemExit(main())
