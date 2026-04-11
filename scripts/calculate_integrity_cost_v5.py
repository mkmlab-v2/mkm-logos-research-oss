#!/usr/bin/env python3
"""Integrity cost v5: v4 wire estimate + virtual B_security (chunk auth, segment auth, fixed envelope).

Builds on evaluate_v4() with merge_gap_bytes default 1 (optimal frontier on current bench).
Security bytes are a configurable spike, not a wire capture of a specific cipher suite.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
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


DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "INTEGRITY_COST_V5_UNIVERSAL_V1.json"


@dataclass(frozen=True)
class SecurityModelV5:
    fixed_per_case: int
    chunk_payload_bytes: int
    per_chunk_overhead: int
    per_merged_segment: int

    def bytes_for_case(self, br: int, exact_match: bool, n_merged: int) -> int:
        br = max(0, int(br))
        cp = max(1, int(self.chunk_payload_bytes))
        chunks = max(1, (br + cp - 1) // cp)
        sec = int(self.fixed_per_case) + chunks * int(self.per_chunk_overhead)
        if not exact_match:
            sec += max(0, int(n_merged)) * int(self.per_merged_segment)
        return sec


# Virtual B_security knobs (not a specific cipher). Presets for stress vs exploratory margin.
SECURITY_PRESETS: dict[str, SecurityModelV5] = {
    "none": SecurityModelV5(
        fixed_per_case=0,
        chunk_payload_bytes=1_000_000_000,
        per_chunk_overhead=0,
        per_merged_segment=0,
    ),
    "stress": SecurityModelV5(
        fixed_per_case=32,
        chunk_payload_bytes=4096,
        per_chunk_overhead=24,
        per_merged_segment=32,
    ),
    "optimistic": SecurityModelV5(
        fixed_per_case=8,
        chunk_payload_bytes=16384,
        per_chunk_overhead=8,
        per_merged_segment=8,
    ),
}


def evaluate_v5(
    report: dict[str, Any],
    raw_by_id: dict[str, str],
    *,
    merge_gap_bytes: int,
    shard_filter: str | None,
    sec: SecurityModelV5,
    include_case_rows: bool,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]] | None]:
    """Returns (v4_summary, v5_summary, rows or None)."""
    v4_summary, rows = evaluate_v4(
        report,
        raw_by_id,
        merge_gap_bytes=merge_gap_bytes,
        shard_filter=shard_filter,
        include_case_rows=True,
    )
    rows = rows or []
    sum_raw = float(v4_summary["bytes_raw_total"])
    sum_wire_v4 = float(v4_summary["total_wire_bytes"])
    sum_sec = 0.0
    out_rows: list[dict[str, Any]] | None = [] if include_case_rows else None

    for r in rows:
        br = int(r["bytes_raw_utf8"])
        exact = bool(r.get("exact_match"))
        n_merged = int(r.get("segment_count_merged") or 0)
        bsec = sec.bytes_for_case(br, exact, n_merged)
        wire_v4 = float(r["total_wire_bytes"])
        wire_v5 = wire_v4 + float(bsec)
        sum_sec += float(bsec)
        if include_case_rows and out_rows is not None:
            rr = dict(r)
            rr["security_bytes_virtual"] = bsec
            rr["total_wire_bytes_v4"] = int(wire_v4)
            rr["total_wire_bytes"] = int(wire_v5)
            rr["real_saving_vs_raw"] = 1.0 - (wire_v5 / float(br)) if br else 0.0
            out_rows.append(rr)

    sum_wire_v5 = sum_wire_v4 + sum_sec
    gsave_v5 = 1.0 - (sum_wire_v5 / sum_raw) if sum_raw else 0.0
    v5_summary = {
        "cases_included": v4_summary["cases_included"],
        "bytes_raw_total": int(sum_raw),
        "bytes_compressed_total": v4_summary["bytes_compressed_total"],
        "total_wire_bytes_v4": int(sum_wire_v4),
        "security_bytes_total_virtual": int(sum_sec),
        "total_wire_bytes": int(sum_wire_v5),
        "global_real_saving_vs_raw": gsave_v5,
    }
    return v4_summary, v5_summary, out_rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Integrity cost v5 (v4 + virtual B_security).")
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--merge-gap-bytes", type=int, default=1, help="Default 1 = sweep optimum on current bench.")
    ap.add_argument("--shard-id", default="", help="If set, only this shard_id in summary.")
    ap.add_argument(
        "--sec-preset",
        choices=sorted(SECURITY_PRESETS.keys()),
        default="stress",
        help="Virtual security bundle: none=v4 parity check, stress=heavy overhead, optimistic=lighter.",
    )
    args = ap.parse_args()

    rep_path = Path(args.report).resolve()
    inp_path = Path(args.input).resolve()
    if not rep_path.is_file() or not inp_path.is_file():
        print("FAIL: report or input not found", file=sys.stderr)
        return 1

    shard_filter = str(args.shard_id).strip() or None
    sec = SECURITY_PRESETS[str(args.sec_preset)]

    report = json.loads(rep_path.read_text(encoding="utf-8"))
    inp = json.loads(inp_path.read_text(encoding="utf-8"))
    cm = report.get("compression_metrics") or {}
    run_cfg = report.get("run_config") or {}

    v4_summary, v5_summary, case_rows = evaluate_v5(
        report,
        {str(c.get("id")): str(c.get("raw_text", "")) for c in (inp.get("compression_cases") or [])},
        merge_gap_bytes=int(args.merge_gap_bytes),
        shard_filter=shard_filter,
        sec=sec,
        include_case_rows=True,
    )
    case_rows = case_rows or []

    payload = {
        "schema": "integrity_cost_model_v5",
        "description": (
            "v4 wire (merge_gap + varint4) plus virtual B_security: fixed + per-chunk + per-merged-segment. "
            "Not a specific AEAD; knobs for protocol-hardening stress tests."
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_report": str(rep_path.relative_to(ROOT)).replace("\\", "/"),
        "source_input": str(inp_path.relative_to(ROOT)).replace("\\", "/"),
        "run_config_snapshot": run_cfg,
        "v5_config": {
            "merge_gap_bytes": int(args.merge_gap_bytes),
            "shard_id_filter": shard_filter,
            "sec_preset": str(args.sec_preset),
            "security_model": {
                "fixed_per_case": sec.fixed_per_case,
                "chunk_payload_bytes": sec.chunk_payload_bytes,
                "per_chunk_overhead": sec.per_chunk_overhead,
                "per_merged_segment": sec.per_merged_segment,
            },
        },
        "summary_v4_reference": {
            **v4_summary,
            "global_token_saving_rate_reported": float(cm.get("global_token_saving_rate") or 0.0)
            if not shard_filter
            else None,
        },
        "summary": {
            **v5_summary,
            "global_token_saving_rate_reported": float(cm.get("global_token_saving_rate") or 0.0)
            if not shard_filter
            else None,
        },
        "cases": case_rows,
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    g = float(v5_summary["global_real_saving_vs_raw"])
    print(
        f"OK: wrote {out_path} cases={v5_summary['cases_included']} preset={args.sec_preset} "
        f"real_saving_v5={g:.4f} B_sec_total={v5_summary['security_bytes_total_virtual']} gap={args.merge_gap_bytes}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
