#!/usr/bin/env python3
"""Integrity cost v6: amortized batch fixed cost + per-case variable security (chunk + segment).

Reuses v4 wire via evaluate_v4. Splits v5-style security into:
  - fixed_per_batch * ceil(N/K) for batch size K (N = included cases)
  - per-case variable: chunk overhead + per-merged-segment (no per-case fixed)

Finds smallest K in 1..N where global_real_saving_vs_raw > 0 (breakeven batch size probe).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.calculate_integrity_cost_v5 import SECURITY_PRESETS, SecurityModelV5  # noqa: E402
from scripts.calculate_integrity_cost_v4 import (  # noqa: E402
    DEFAULT_INPUT,
    DEFAULT_REPORT,
    evaluate_v4,
)

DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "INTEGRITY_COST_V6_AMORTIZED_V1.json"


def variable_security_bytes(sec: SecurityModelV5, br: int, exact_match: bool, n_merged: int) -> int:
    """Chunk + segment terms only (v5 fixed_per_case excluded)."""
    br = max(0, int(br))
    cp = max(1, int(sec.chunk_payload_bytes))
    chunks = max(1, (br + cp - 1) // cp)
    v = chunks * int(sec.per_chunk_overhead)
    if not exact_match:
        v += max(0, int(n_merged)) * int(sec.per_merged_segment)
    return v


def evaluate_v6_amortized(
    report: dict[str, Any],
    raw_by_id: dict[str, str],
    *,
    merge_gap_bytes: int,
    shard_filter: str | None,
    sec: SecurityModelV5,
    fixed_per_batch: int,
    batch_size_k: int,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Single batch size K. Returns (v4_summary, v6_summary, case rows)."""
    v4_summary, rows = evaluate_v4(
        report,
        raw_by_id,
        merge_gap_bytes=merge_gap_bytes,
        shard_filter=shard_filter,
        include_case_rows=True,
    )
    rows = rows or []
    n = len(rows)
    sum_raw = float(v4_summary["bytes_raw_total"])
    sum_wire_v4 = float(v4_summary["total_wire_bytes"])
    sum_var = 0.0
    out_rows: list[dict[str, Any]] = []

    batches = int(math.ceil(n / float(max(1, batch_size_k)))) if n else 0
    total_fixed = int(max(0, int(fixed_per_batch))) * max(0, batches)

    for r in rows:
        br = int(r["bytes_raw_utf8"])
        exact = bool(r.get("exact_match"))
        n_merged = int(r.get("segment_count_merged") or 0)
        vsec = variable_security_bytes(sec, br, exact, n_merged)
        wire_v4 = float(r["total_wire_bytes"])
        amort_fixed_share = float(total_fixed) / float(n) if n else 0.0
        wire_v6 = wire_v4 + vsec + amort_fixed_share
        sum_var += float(vsec)
        rr = dict(r)
        rr["variable_security_bytes_virtual"] = vsec
        rr["amortized_fixed_bytes_per_case"] = amort_fixed_share
        rr["total_wire_bytes_v4"] = int(wire_v4)
        rr["total_wire_bytes"] = int(round(wire_v6))
        rr["real_saving_vs_raw"] = 1.0 - (wire_v6 / float(br)) if br else 0.0
        out_rows.append(rr)

    sum_wire_v6 = sum_wire_v4 + sum_var + float(total_fixed)
    gsave = 1.0 - (sum_wire_v6 / sum_raw) if sum_raw else 0.0
    v6_summary = {
        "cases_included": n,
        "batch_size_k": int(batch_size_k),
        "batch_count": batches,
        "fixed_per_batch_bytes": int(fixed_per_batch),
        "total_fixed_bytes_amortized_model": int(total_fixed),
        "bytes_raw_total": int(sum_raw),
        "bytes_compressed_total": v4_summary["bytes_compressed_total"],
        "total_wire_bytes_v4": int(sum_wire_v4),
        "variable_security_bytes_total": int(sum_var),
        "total_wire_bytes": int(sum_wire_v6),
        "global_real_saving_vs_raw": gsave,
    }
    return v4_summary, v6_summary, out_rows


def sweep_batch_sizes(
    report: dict[str, Any],
    raw_by_id: dict[str, str],
    *,
    merge_gap_bytes: int,
    shard_filter: str | None,
    sec: SecurityModelV5,
    fixed_per_batch: int,
    k_max: int,
) -> tuple[list[dict[str, Any]], int | None]:
    """Returns (rows one per K, breakeven_k smallest K with gsave > 0 or None)."""
    v4_summary, rows = evaluate_v4(
        report,
        raw_by_id,
        merge_gap_bytes=merge_gap_bytes,
        shard_filter=shard_filter,
        include_case_rows=True,
    )
    rows = rows or []
    n = len(rows)
    if n == 0:
        return [], None

    sum_raw = float(v4_summary["bytes_raw_total"])
    sum_wire_v4 = float(v4_summary["total_wire_bytes"])
    sum_var = 0.0
    for r in rows:
        br = int(r["bytes_raw_utf8"])
        exact = bool(r.get("exact_match"))
        n_merged = int(r.get("segment_count_merged") or 0)
        sum_var += float(variable_security_bytes(sec, br, exact, n_merged))

    F = int(max(0, fixed_per_batch))
    sweep_out: list[dict[str, Any]] = []
    breakeven: int | None = None
    upper = min(int(k_max), n) if k_max else n
    for k in range(1, upper + 1):
        batches = int(math.ceil(n / float(k)))
        total_fixed = F * batches
        sum_wire = sum_wire_v4 + sum_var + float(total_fixed)
        gsave = 1.0 - (sum_wire / sum_raw) if sum_raw else 0.0
        sweep_out.append(
            {
                "batch_size_k": k,
                "batch_count": batches,
                "total_fixed_bytes": int(total_fixed),
                "global_real_saving_vs_raw": gsave,
            }
        )
        if breakeven is None and gsave > 0:
            breakeven = k

    return sweep_out, breakeven


def main() -> int:
    ap = argparse.ArgumentParser(description="Integrity cost v6 (amortized batch B_security).")
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--merge-gap-bytes", type=int, default=1)
    ap.add_argument("--shard-id", default="")
    ap.add_argument(
        "--sec-preset",
        choices=sorted(SECURITY_PRESETS.keys()),
        default="optimistic",
        help="Variable chunk/segment knobs; use optimistic/stress (not none).",
    )
    ap.add_argument(
        "--fixed-per-batch",
        type=int,
        default=None,
        help="Bytes charged once per batch (default: same as preset's fixed_per_case).",
    )
    ap.add_argument(
        "--batch-size",
        type=int,
        default=0,
        help="If >0, emit detailed case rows for this K only; if 0, sweep only.",
    )
    ap.add_argument(
        "--sweep-max-k",
        type=int,
        default=0,
        help="Max K for sweep (default: N cases included).",
    )
    args = ap.parse_args()

    if str(args.sec_preset) == "none":
        print("FAIL: use sec-preset optimistic or stress (none has no variable security)", file=sys.stderr)
        return 1

    rep_path = Path(args.report).resolve()
    inp_path = Path(args.input).resolve()
    if not rep_path.is_file() or not inp_path.is_file():
        print("FAIL: report or input not found", file=sys.stderr)
        return 1

    shard_filter = str(args.shard_id).strip() or None
    sec = SECURITY_PRESETS[str(args.sec_preset)]
    fixed_pb = int(args.fixed_per_batch) if args.fixed_per_batch is not None else int(sec.fixed_per_case)

    report = json.loads(rep_path.read_text(encoding="utf-8"))
    inp = json.loads(inp_path.read_text(encoding="utf-8"))
    raw_by_id = {str(c.get("id")): str(c.get("raw_text", "")) for c in (inp.get("compression_cases") or [])}
    cm = report.get("compression_metrics") or {}
    run_cfg = report.get("run_config") or {}

    v4_summary, _ = evaluate_v4(
        report,
        raw_by_id,
        merge_gap_bytes=int(args.merge_gap_bytes),
        shard_filter=shard_filter,
        include_case_rows=False,
    )
    n = int(v4_summary["cases_included"])
    k_max = int(args.sweep_max_k) if int(args.sweep_max_k) > 0 else n

    sweep_rows, breakeven_k = sweep_batch_sizes(
        report,
        raw_by_id,
        merge_gap_bytes=int(args.merge_gap_bytes),
        shard_filter=shard_filter,
        sec=sec,
        fixed_per_batch=fixed_pb,
        k_max=k_max,
    )

    sweep_best: dict[str, Any] | None = None
    if sweep_rows:
        best_row = max(sweep_rows, key=lambda r: float(r["global_real_saving_vs_raw"]))
        sweep_best = {
            "batch_size_k": int(best_row["batch_size_k"]),
            "global_real_saving_vs_raw": float(best_row["global_real_saving_vs_raw"]),
            "total_fixed_bytes": int(best_row["total_fixed_bytes"]),
        }

    detail_cases: list[dict[str, Any]] | None = None
    v6_one: dict[str, Any] | None = None
    if int(args.batch_size) > 0:
        _, v6_one, detail_cases = evaluate_v6_amortized(
            report,
            raw_by_id,
            merge_gap_bytes=int(args.merge_gap_bytes),
            shard_filter=shard_filter,
            sec=sec,
            fixed_per_batch=fixed_pb,
            batch_size_k=int(args.batch_size),
        )

    payload = {
        "schema": "integrity_cost_model_v6_amortized",
        "description": (
            "v4 wire + variable security (chunk + merged segments) + fixed_per_batch * ceil(N/K). "
            "Breakeven: smallest K with global_real_saving_vs_raw > 0 in sweep."
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_report": str(rep_path.relative_to(ROOT)).replace("\\", "/"),
        "source_input": str(inp_path.relative_to(ROOT)).replace("\\", "/"),
        "run_config_snapshot": run_cfg,
        "v6_config": {
            "merge_gap_bytes": int(args.merge_gap_bytes),
            "shard_id_filter": shard_filter,
            "sec_preset": str(args.sec_preset),
            "fixed_per_batch_bytes": fixed_pb,
            "variable_security_model": {
                "chunk_payload_bytes": sec.chunk_payload_bytes,
                "per_chunk_overhead": sec.per_chunk_overhead,
                "per_merged_segment": sec.per_merged_segment,
            },
            "cases_included_n": n,
            "sweep_max_k": k_max,
        },
        "summary_v4_reference": {
            **v4_summary,
            "global_token_saving_rate_reported": float(cm.get("global_token_saving_rate") or 0.0)
            if not shard_filter
            else None,
        },
        "breakeven_batch_size_k": breakeven_k,
        "sweep_best_by_global_saving": sweep_best,
        "batch_size_sweep": sweep_rows,
        "detail_batch_size_k": int(args.batch_size) if int(args.batch_size) > 0 else None,
        "summary_at_detail_k": v6_one,
        "cases_at_detail_k": detail_cases,
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"OK: wrote {out_path} N={n} preset={args.sec_preset} fixed_per_batch={fixed_pb} breakeven_k={breakeven_k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
