#!/usr/bin/env python3
"""Integrity cost v7: session-level security (single virtual envelope over the whole cohort).

Adds zero per-chunk / per-segment tax; only session_fixed_bytes once per evaluated cohort.
Contrasts with v5/v6 granular auth: shows headroom when integrity is amortized to one MAC/AEAD tag.

Breakeven: max session overhead before global_real_saving_vs_raw <= 0 is (bytes_raw_total - total_wire_bytes_v4).
"""

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

from scripts.calculate_integrity_cost_v4 import (  # noqa: E402
    DEFAULT_INPUT,
    DEFAULT_REPORT,
    evaluate_v4,
)

DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "INTEGRITY_COST_V7_SESSION_V1.json"


def evaluate_v7_session(
    report: dict[str, Any],
    raw_by_id: dict[str, str],
    *,
    merge_gap_bytes: int,
    shard_filter: str | None,
    session_fixed_bytes: int,
    include_case_rows: bool,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]] | None]:
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
    F = max(0, int(session_fixed_bytes))
    share = float(F) / float(n) if n else 0.0
    sum_wire_v7 = sum_wire_v4 + float(F)
    gsave = 1.0 - (sum_wire_v7 / sum_raw) if sum_raw else 0.0

    headroom = max(0.0, sum_raw - sum_wire_v4)

    v7_summary = {
        "cases_included": n,
        "session_fixed_bytes_total": F,
        "session_fixed_amortized_per_case": share,
        "bytes_raw_total": int(sum_raw),
        "bytes_compressed_total": v4_summary["bytes_compressed_total"],
        "total_wire_bytes_v4": int(sum_wire_v4),
        "total_wire_bytes": int(sum_wire_v7),
        "global_real_saving_vs_raw": gsave,
        "headroom_bytes_before_nonpositive_saving": int(headroom),
        "session_fixed_at_nonpositive_threshold": int(headroom) + 1,
    }

    out_rows: list[dict[str, Any]] | None = None
    if include_case_rows:
        out_rows = []
        for r in rows:
            br = int(r["bytes_raw_utf8"])
            wire_v4 = float(r["total_wire_bytes"])
            wire_v7 = wire_v4 + share
            rr = dict(r)
            rr["session_fixed_amortized_bytes"] = share
            rr["total_wire_bytes_v4"] = int(wire_v4)
            rr["total_wire_bytes"] = int(round(wire_v7))
            rr["real_saving_vs_raw"] = 1.0 - (wire_v7 / float(br)) if br else 0.0
            out_rows.append(rr)

    ref = {**v4_summary, "headroom_bytes": int(headroom)}
    return ref, v7_summary, out_rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Integrity cost v7 (session-only B_security).")
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--merge-gap-bytes", type=int, default=1)
    ap.add_argument("--shard-id", default="")
    ap.add_argument(
        "--session-fixed-bytes",
        type=int,
        default=64,
        help="Virtual one-shot session integrity cost (MAC/AEAD tag budget) over whole cohort.",
    )
    ap.add_argument(
        "--session-sweep",
        default="",
        help="Optional comma-separated session_fixed values (e.g. 0,32,64,128,256,382,400).",
    )
    args = ap.parse_args()

    rep_path = Path(args.report).resolve()
    inp_path = Path(args.input).resolve()
    if not rep_path.is_file() or not inp_path.is_file():
        print("FAIL: report or input not found", file=sys.stderr)
        return 1

    shard_filter = str(args.shard_id).strip() or None
    report = json.loads(rep_path.read_text(encoding="utf-8"))
    inp = json.loads(inp_path.read_text(encoding="utf-8"))
    raw_by_id = {str(c.get("id")): str(c.get("raw_text", "")) for c in (inp.get("compression_cases") or [])}
    cm = report.get("compression_metrics") or {}
    run_cfg = report.get("run_config") or {}

    sweep_vals: list[int] = []
    if str(args.session_sweep).strip():
        sweep_vals = [int(x.strip()) for x in str(args.session_sweep).split(",") if x.strip()]

    if sweep_vals:
        sweep_out: list[dict[str, Any]] = []
        for F in sweep_vals:
            v4_ref, v7_s, _ = evaluate_v7_session(
                report,
                raw_by_id,
                merge_gap_bytes=int(args.merge_gap_bytes),
                shard_filter=shard_filter,
                session_fixed_bytes=F,
                include_case_rows=False,
            )
            sweep_out.append(
                {
                    "session_fixed_bytes": F,
                    "global_real_saving_vs_raw": float(v7_s["global_real_saving_vs_raw"]),
                    "total_wire_bytes": int(v7_s["total_wire_bytes"]),
                }
            )
        v4_ref, v7_summary, case_rows = evaluate_v7_session(
            report,
            raw_by_id,
            merge_gap_bytes=int(args.merge_gap_bytes),
            shard_filter=shard_filter,
            session_fixed_bytes=int(args.session_fixed_bytes),
            include_case_rows=True,
        )
        payload = {
            "schema": "integrity_cost_model_v7_session",
            "description": (
                "v4 wire + single session_fixed_bytes over cohort (no per-chunk/per-segment). "
                "headroom_bytes_before_nonpositive_saving = bytes_raw_total - total_wire_bytes_v4."
            ),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_report": str(rep_path.relative_to(ROOT)).replace("\\", "/"),
            "source_input": str(inp_path.relative_to(ROOT)).replace("\\", "/"),
            "run_config_snapshot": run_cfg,
            "v7_config": {
                "merge_gap_bytes": int(args.merge_gap_bytes),
                "shard_id_filter": shard_filter,
                "session_fixed_bytes_primary": int(args.session_fixed_bytes),
                "session_sweep_values": sweep_vals,
            },
            "summary_v4_reference": {
                **v4_ref,
                "global_token_saving_rate_reported": float(cm.get("global_token_saving_rate") or 0.0)
                if not shard_filter
                else None,
            },
            "summary": {
                **v7_summary,
                "global_token_saving_rate_reported": float(cm.get("global_token_saving_rate") or 0.0)
                if not shard_filter
                else None,
            },
            "session_fixed_sweep": sweep_out,
            "cases": case_rows or [],
        }
    else:
        v4_ref, v7_summary, case_rows = evaluate_v7_session(
            report,
            raw_by_id,
            merge_gap_bytes=int(args.merge_gap_bytes),
            shard_filter=shard_filter,
            session_fixed_bytes=int(args.session_fixed_bytes),
            include_case_rows=True,
        )
        payload = {
            "schema": "integrity_cost_model_v7_session",
            "description": (
                "v4 wire + single session_fixed_bytes over cohort (no per-chunk/per-segment). "
                "headroom_bytes_before_nonpositive_saving = bytes_raw_total - total_wire_bytes_v4."
            ),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_report": str(rep_path.relative_to(ROOT)).replace("\\", "/"),
            "source_input": str(inp_path.relative_to(ROOT)).replace("\\", "/"),
            "run_config_snapshot": run_cfg,
            "v7_config": {
                "merge_gap_bytes": int(args.merge_gap_bytes),
                "shard_id_filter": shard_filter,
                "session_fixed_bytes": int(args.session_fixed_bytes),
            },
            "summary_v4_reference": {
                **v4_ref,
                "global_token_saving_rate_reported": float(cm.get("global_token_saving_rate") or 0.0)
                if not shard_filter
                else None,
            },
            "summary": {
                **v7_summary,
                "global_token_saving_rate_reported": float(cm.get("global_token_saving_rate") or 0.0)
                if not shard_filter
                else None,
            },
            "cases": case_rows or [],
        }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    g = float(payload["summary"]["global_real_saving_vs_raw"])
    print(
        f"OK: wrote {out_path} session_fixed={args.session_fixed_bytes} "
        f"real_saving_v7={g:.4f} headroom={payload['summary']['headroom_bytes_before_nonpositive_saving']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
