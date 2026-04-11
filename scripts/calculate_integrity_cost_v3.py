#!/usr/bin/env python3
"""Integrity wire cost v3: opcode patch bytes + per-segment framing overhead.

Extends v2 opcode model: side_channel = opcode_payload_bytes + n_non_equal_segments * overhead.

Overhead sweep (default 0,8,16,24,32) shows how fast profit erodes when framing grows.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_V2_UNIVERSAL_SHARD_PROBE_V1.json"
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "INTEGRITY_COST_V3_UNIVERSAL_V1.json"


def _b(s: str) -> int:
    return len(s.encode("utf-8"))


def _opcode_payload_and_segments(rec_b: bytes, raw_b: bytes) -> tuple[int, int]:
    sm = difflib.SequenceMatcher(None, rec_b, raw_b)
    cost = 0
    n_seg = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        n_seg += 1
        if tag == "delete":
            cost += i2 - i1
        elif tag == "insert":
            cost += j2 - j1
        else:
            cost += (i2 - i1) + (j2 - j1)
    return cost, n_seg


def main() -> int:
    ap = argparse.ArgumentParser(description="Integrity cost v3 (opcode + framing overhead).")
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--overhead-sweep",
        default="0,8,16,24,32",
        help="Comma-separated extra bytes per non-equal opcode segment",
    )
    args = ap.parse_args()

    rep_path = Path(args.report).resolve()
    inp_path = Path(args.input).resolve()
    if not rep_path.is_file() or not inp_path.is_file():
        print("FAIL: report or input not found", file=sys.stderr)
        return 1

    overheads = [int(x.strip()) for x in str(args.overhead_sweep).split(",") if x.strip()]

    report = json.loads(rep_path.read_text(encoding="utf-8"))
    inp = json.loads(inp_path.read_text(encoding="utf-8"))
    raw_by_id = {str(c.get("id")): str(c.get("raw_text", "")) for c in (inp.get("compression_cases") or [])}

    cases = (report.get("compression_metrics") or {}).get("cases") or []
    cm = report.get("compression_metrics") or {}
    run_cfg = report.get("run_config") or {}

    rows_base: list[dict[str, Any]] = []
    for row in cases:
        cid = str(row.get("id", ""))
        raw = raw_by_id.get(cid, "")
        rec = str(row.get("reconstructed_text_effective", ""))
        comp = str(row.get("compressed_text_effective", ""))
        route = row.get("route") if isinstance(row.get("route"), dict) else {}
        shard = str(route.get("shard_id") or "_no_route_")

        br = _b(raw)
        bc = _b(comp)
        if br <= 0:
            continue

        mismatch = raw != rec
        rec_b = rec.encode("utf-8")
        raw_b = raw.encode("utf-8")
        payload, n_seg = _opcode_payload_and_segments(rec_b, raw_b) if mismatch else (0, 0)

        rows_base.append(
            {
                "id": cid,
                "shard_id": shard,
                "bytes_raw_utf8": br,
                "bytes_compressed_utf8": bc,
                "exact_match": not mismatch,
                "opcode_payload_bytes": payload,
                "non_equal_segment_count": n_seg,
            }
        )

    R = float(sum(r["bytes_raw_utf8"] for r in rows_base))
    sweep_out: list[dict[str, Any]] = []

    for oh in overheads:
        sum_wire = 0.0
        for i, row in enumerate(rows_base):
            bc = row["bytes_compressed_utf8"]
            br = row["bytes_raw_utf8"]
            if row["exact_match"]:
                sum_wire += bc
            else:
                side = row["opcode_payload_bytes"] + row["non_equal_segment_count"] * oh
                sum_wire += bc + side
        sav = 1.0 - (sum_wire / R) if R else 0.0
        sweep_out.append(
            {
                "per_segment_overhead_bytes": oh,
                "total_wire_bytes": int(sum_wire),
                "global_real_saving_vs_raw": sav,
            }
        )

    cases_out: list[dict[str, Any]] = []
    default_oh = 8
    for row in rows_base:
        br = row["bytes_raw_utf8"]
        bc = row["bytes_compressed_utf8"]
        if row["exact_match"]:
            tw = bc
            side = 0
        else:
            side = row["opcode_payload_bytes"] + row["non_equal_segment_count"] * default_oh
            tw = bc + side
        cases_out.append(
            {
                **row,
                "side_channel_opcode_framed_bytes": side,
                "per_segment_overhead_bytes": default_oh,
                "total_wire_bytes": tw,
                "real_saving_vs_raw": 1.0 - (tw / float(br)),
            }
        )

    payload = {
        "schema": "integrity_cost_model_v3",
        "description": (
            "Opcode payload plus per non-equal segment framing overhead. "
            "overhead=0 matches v2 opcode wire. Sweep shows sensitivity to protocol cost."
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_report": str(rep_path.relative_to(ROOT)).replace("\\", "/"),
        "source_input": str(inp_path.relative_to(ROOT)).replace("\\", "/"),
        "run_config_snapshot": run_cfg,
        "summary": {
            "case_count": len(rows_base),
            "bytes_raw_total": int(R),
            "bytes_compressed_total": sum(r["bytes_compressed_utf8"] for r in rows_base),
            "global_token_saving_rate_reported": float(cm.get("global_token_saving_rate") or 0.0),
            "framing_overhead_sweep": sweep_out,
            "default_per_segment_overhead_bytes": default_oh,
        },
        "cases": cases_out,
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    mid = next((x for x in sweep_out if x["per_segment_overhead_bytes"] == 8), sweep_out[-1])
    print(f"OK: wrote {out_path} overhead=8 real_saving={mid['global_real_saving_vs_raw']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
