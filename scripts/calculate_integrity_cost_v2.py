#!/usr/bin/env python3
"""Integrity wire cost v2: differential patch instead of full raw on side channel.

Estimates side-channel bytes as:
  - diff_uncompressed: UTF-8 length of unified_diff(rec, raw) text
  - diff_zlib: zlib.compress(diff_uncompressed, level=6) length
  - opcode_bytes: byte-level SequenceMatcher non-equal segments (insert+delete sizes)

Total wire = bytes_compressed_utf8 + side (each model).
Real saving vs raw-only = 1 - total_wire / bytes_raw.

Compare with v1 full-raw side channel (included in output as reference).
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
import zlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_V2_UNIVERSAL_SHARD_PROBE_V1.json"
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "INTEGRITY_COST_V2_UNIVERSAL_V1.json"


def _b(s: str) -> int:
    return len(s.encode("utf-8"))


def _unified_diff_bytes(raw: str, rec: str) -> bytes:
    lines_r = rec.splitlines(keepends=True)
    lines_w = raw.splitlines(keepends=True)
    if not lines_r and not lines_w:
        return b""
    ud = list(
        difflib.unified_diff(
            lines_r,
            lines_w,
            fromfile="reconstructed",
            tofile="raw",
            n=3,
        )
    )
    return "".join(ud).encode("utf-8")


def _opcode_patch_bytes(rec_b: bytes, raw_b: bytes) -> int:
    sm = difflib.SequenceMatcher(None, rec_b, raw_b)
    cost = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            cost += i2 - i1
        elif tag == "insert":
            cost += j2 - j1
        else:
            cost += (i2 - i1) + (j2 - j1)
    return cost


def main() -> int:
    ap = argparse.ArgumentParser(description="Integrity cost v2 (differential patch models).")
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rep_path = Path(args.report).resolve()
    inp_path = Path(args.input).resolve()
    if not rep_path.is_file() or not inp_path.is_file():
        print("FAIL: report or input not found", file=sys.stderr)
        return 1

    report = json.loads(rep_path.read_text(encoding="utf-8"))
    inp = json.loads(inp_path.read_text(encoding="utf-8"))
    raw_by_id = {str(c.get("id")): str(c.get("raw_text", "")) for c in (inp.get("compression_cases") or [])}

    cases = (report.get("compression_metrics") or {}).get("cases") or []
    cm = report.get("compression_metrics") or {}
    run_cfg = report.get("run_config") or {}

    rows_out: list[dict[str, Any]] = []
    agg = {
        "raw": 0,
        "comp": 0,
        "side_v1_full_raw": 0,
        "side_diff_unc": 0,
        "side_diff_zlib": 0,
        "side_opcode": 0,
        "wire_v1": 0,
        "wire_diff_unc": 0,
        "wire_diff_zlib": 0,
        "wire_opcode": 0,
    }

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
        side_v1 = br if mismatch else 0

        rec_b = rec.encode("utf-8")
        raw_b = raw.encode("utf-8")
        diff_b = _unified_diff_bytes(raw, rec) if mismatch else b""
        side_unc = len(diff_b)
        side_zlib = len(zlib.compress(diff_b, level=6)) if mismatch else 0
        side_op = _opcode_patch_bytes(rec_b, raw_b) if mismatch else 0

        wire_v1 = bc + side_v1
        wire_unc = bc + side_unc
        wire_zlib = bc + side_zlib
        wire_op = bc + side_op

        agg["raw"] += br
        agg["comp"] += bc
        agg["side_v1_full_raw"] += side_v1
        agg["side_diff_unc"] += side_unc
        agg["side_diff_zlib"] += side_zlib
        agg["side_opcode"] += side_op
        agg["wire_v1"] += wire_v1
        agg["wire_diff_unc"] += wire_unc
        agg["wire_diff_zlib"] += wire_zlib
        agg["wire_opcode"] += wire_op

        rows_out.append(
            {
                "id": cid,
                "shard_id": shard,
                "bytes_raw_utf8": br,
                "bytes_compressed_utf8": bc,
                "exact_match": not mismatch,
                "side_channel_v1_full_raw": side_v1,
                "side_channel_diff_uncompressed": side_unc,
                "side_channel_diff_zlib6": side_zlib,
                "side_channel_opcode_sum_bytes": side_op,
                "total_wire_v1": wire_v1,
                "total_wire_diff_unc": wire_unc,
                "total_wire_diff_zlib": wire_zlib,
                "total_wire_opcode": wire_op,
                "real_saving_vs_raw_v1": 1.0 - (wire_v1 / float(br)),
                "real_saving_vs_raw_diff_unc": 1.0 - (wire_unc / float(br)),
                "real_saving_vs_raw_diff_zlib": 1.0 - (wire_zlib / float(br)),
                "real_saving_vs_raw_opcode": 1.0 - (wire_op / float(br)),
                "reported_token_saving_rate": row.get("token_saving_rate"),
            }
        )

    R = float(agg["raw"])
    summary = {
        "case_count": len(rows_out),
        "bytes_raw_total": int(agg["raw"]),
        "bytes_compressed_total": int(agg["comp"]),
        "global_token_saving_rate_reported": float(cm.get("global_token_saving_rate") or 0.0),
        "global_saving_vs_raw_compressed_only_naive_bytes": 1.0 - (agg["comp"] / R) if R else 0.0,
        "v1_full_raw_side_channel": {
            "side_channel_bytes_total": int(agg["side_v1_full_raw"]),
            "total_wire_bytes": int(agg["wire_v1"]),
            "global_real_saving_vs_raw": 1.0 - (agg["wire_v1"] / R) if R else 0.0,
        },
        "v2_diff_uncompressed": {
            "side_channel_bytes_total": int(agg["side_diff_unc"]),
            "total_wire_bytes": int(agg["wire_diff_unc"]),
            "global_real_saving_vs_raw": 1.0 - (agg["wire_diff_unc"] / R) if R else 0.0,
        },
        "v2_diff_zlib6": {
            "side_channel_bytes_total": int(agg["side_diff_zlib"]),
            "total_wire_bytes": int(agg["wire_diff_zlib"]),
            "global_real_saving_vs_raw": 1.0 - (agg["wire_diff_zlib"] / R) if R else 0.0,
        },
        "v2_opcode_byte_segments": {
            "side_channel_bytes_total": int(agg["side_opcode"]),
            "total_wire_bytes": int(agg["wire_opcode"]),
            "global_real_saving_vs_raw": 1.0 - (agg["wire_opcode"] / R) if R else 0.0,
        },
    }

    payload = {
        "schema": "integrity_cost_model_v2",
        "description": (
            "Differential patch models for side channel when raw!=rec. "
            "unified_diff is a text proxy; zlib is optimistic wire size; opcode sum is a structural upper bound. "
            "None of these include framing/encryption overhead."
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_report": str(rep_path.relative_to(ROOT)).replace("\\", "/"),
        "source_input": str(inp_path.relative_to(ROOT)).replace("\\", "/"),
        "run_config_snapshot": run_cfg,
        "summary": summary,
        "cases": rows_out,
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    z = summary["v2_diff_zlib6"]["global_real_saving_vs_raw"]
    print(f"OK: wrote {out_path} real_saving_zlib={z:.4f} real_saving_v1={summary['v1_full_raw_side_channel']['global_real_saving_vs_raw']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
