#!/usr/bin/env python3
"""Sweep merge_gap_bytes (default 1..32) for v4 integrity cost; reuse evaluate_v4()."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.calculate_integrity_cost_v4 import DEFAULT_INPUT, DEFAULT_REPORT, evaluate_v4  # noqa: E402


def _best(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    best = max(rows, key=lambda r: float(r.get("global_real_saving_vs_raw") or 0.0))
    return {
        "merge_gap_bytes": int(best["merge_gap_bytes"]),
        "global_real_saving_vs_raw": float(best["global_real_saving_vs_raw"]),
        "cases_included": int(best["cases_included"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep v4 merge_gap_bytes for real saving vs raw.")
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs" / "final" / "artifacts" / "INTEGRITY_V4_MERGE_GAP_SWEEP_V1.json",
    )
    ap.add_argument("--gap-min", type=int, default=1)
    ap.add_argument("--gap-max", type=int, default=32)
    ap.add_argument(
        "--extra-shards",
        default="zone_c_hangul",
        help="Comma-separated shard_id values for per-shard sweep (empty to skip).",
    )
    args = ap.parse_args()

    rep_path = Path(args.report).resolve()
    inp_path = Path(args.input).resolve()
    if not rep_path.is_file() or not inp_path.is_file():
        print("FAIL: report or input not found", file=sys.stderr)
        return 1

    g0, g1 = int(args.gap_min), int(args.gap_max)
    if g0 < 1 or g1 < g0 or g1 > 256:
        print("FAIL: invalid gap range", file=sys.stderr)
        return 1

    report = json.loads(rep_path.read_text(encoding="utf-8"))
    inp = json.loads(inp_path.read_text(encoding="utf-8"))
    raw_by_id = {str(c.get("id")): str(c.get("raw_text", "")) for c in (inp.get("compression_cases") or [])}

    gaps = list(range(g0, g1 + 1))
    universal: list[dict[str, Any]] = []
    for gap in gaps:
        summary, _ = evaluate_v4(
            report,
            raw_by_id,
            merge_gap_bytes=gap,
            shard_filter=None,
            include_case_rows=False,
        )
        universal.append({"merge_gap_bytes": gap, **summary})

    extra = [s.strip() for s in str(args.extra_shards).split(",") if s.strip()]
    by_shard: dict[str, list[dict[str, Any]]] = {}
    for shard in extra:
        rows_s: list[dict[str, Any]] = []
        for gap in gaps:
            summary, _ = evaluate_v4(
                report,
                raw_by_id,
                merge_gap_bytes=gap,
                shard_filter=shard,
                include_case_rows=False,
            )
            rows_s.append({"merge_gap_bytes": gap, **summary})
        by_shard[shard] = rows_s

    payload = {
        "schema": "integrity_v4_merge_gap_sweep_v1",
        "description": "merge_gap_bytes sweep; varint4 framing; no B_security.",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_report": str(rep_path.relative_to(ROOT)).replace("\\", "/"),
        "source_input": str(inp_path.relative_to(ROOT)).replace("\\", "/"),
        "gap_range": {"min": g0, "max": g1},
        "universal": universal,
        "by_shard": by_shard,
        "best": {
            "universal": _best(universal),
            **{f"shard:{k}": _best(v) for k, v in by_shard.items()},
        },
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    bu = payload["best"]["universal"]
    print(f"OK: wrote {out_path}")
    if bu:
        print(
            f"best universal: gap={bu['merge_gap_bytes']} "
            f"real_saving={bu['global_real_saving_vs_raw']:.6f} cases={bu['cases_included']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
