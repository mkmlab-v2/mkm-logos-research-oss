#!/usr/bin/env python3
"""Integrity cost v4: merged edit segments + varint-style framing estimate.

Merges SequenceMatcher opcodes when separated only by short 'equal' runs (merge_gap_bytes),
reducing segment count N. Per-segment overhead uses protobuf-like varint byte lengths for
four fields (rec offset, raw offset, rec span len, raw span len) — a protocol spike, not wire truth.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_V2_UNIVERSAL_SHARD_PROBE_V1.json"
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "INTEGRITY_COST_V4_UNIVERSAL_V1.json"


def _b(s: str) -> int:
    return len(s.encode("utf-8"))


def varint_byte_len(n: int) -> int:
    """Protobuf-style varint: 7 bits per byte; non-negative only."""
    n = max(0, int(n))
    if n == 0:
        return 1
    b = 0
    while n > 0:
        b += 1
        n >>= 7
    return b


def framing_bytes_varint4(rec_off: int, raw_off: int, rec_span: int, raw_span: int) -> int:
    return (
        varint_byte_len(rec_off)
        + varint_byte_len(raw_off)
        + varint_byte_len(rec_span)
        + varint_byte_len(raw_span)
    )


@dataclass
class MergedSeg:
    i1: int
    i2: int
    j1: int
    j2: int

    @property
    def payload_bytes(self) -> int:
        return (self.i2 - self.i1) + (self.j2 - self.j1)


def merge_opcodes_with_gap(
    opcodes: list[tuple[str, int, int, int, int]],
    *,
    merge_gap_bytes: int,
) -> list[MergedSeg]:
    """Merge non-equal runs; absorb 'equal' segments of length <= merge_gap into one edit block."""
    buffer: list[tuple[str, int, int, int, int]] = []
    out: list[MergedSeg] = []

    def flush() -> None:
        if not buffer:
            return
        i1 = min(x[1] for x in buffer)
        i2 = max(x[2] for x in buffer)
        j1 = min(x[3] for x in buffer)
        j2 = max(x[4] for x in buffer)
        out.append(MergedSeg(i1=i1, i2=i2, j1=j1, j2=j2))
        buffer.clear()

    for op in opcodes:
        tag, i1, i2, j1, j2 = op
        if tag == "equal":
            elen = i2 - i1
            if elen <= merge_gap_bytes and buffer:
                buffer.append(op)
            else:
                flush()
        else:
            buffer.append(op)
    flush()
    return out


def analyze_case(
    raw_b: bytes,
    rec_b: bytes,
    *,
    merge_gap_bytes: int,
) -> tuple[int, int, int, list[MergedSeg], int]:
    """Returns payload_sum, sm_non_equal_count, merged_count, merged_segments, framing_bytes."""
    sm = difflib.SequenceMatcher(None, rec_b, raw_b)
    opcodes = sm.get_opcodes()
    raw_n = sum(1 for t, _, _, _, _ in opcodes if t != "equal")
    merged = merge_opcodes_with_gap(list(opcodes), merge_gap_bytes=merge_gap_bytes)
    payload = sum(m.payload_bytes for m in merged)
    framing = sum(
        framing_bytes_varint4(m.i1, m.j1, m.i2 - m.i1, m.j2 - m.j1) for m in merged
    )
    return payload, raw_n, len(merged), merged, framing


def main() -> int:
    ap = argparse.ArgumentParser(description="Integrity cost v4 (merge + varint framing).")
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--merge-gap-bytes", type=int, default=4)
    ap.add_argument(
        "--shard-id",
        default="",
        help="If set, only cases with this shard_id (e.g. zone_c_hangul) in global summary.",
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

    cases = (report.get("compression_metrics") or {}).get("cases") or []
    cm = report.get("compression_metrics") or {}
    run_cfg = report.get("run_config") or {}

    rows: list[dict[str, Any]] = []
    sum_raw = 0.0
    sum_comp = 0.0
    sum_wire = 0.0
    n_included = 0

    for row in cases:
        cid = str(row.get("id", ""))
        raw = raw_by_id.get(cid, "")
        rec = str(row.get("reconstructed_text_effective", ""))
        comp = str(row.get("compressed_text_effective", ""))
        route = row.get("route") if isinstance(row.get("route"), dict) else {}
        shard = str(route.get("shard_id") or "_no_route_")

        if shard_filter and shard != shard_filter:
            continue

        br = _b(raw)
        bc = _b(comp)
        if br <= 0:
            continue

        raw_b = raw.encode("utf-8")
        rec_b = rec.encode("utf-8")

        if raw == rec:
            wire = float(bc)
            rows.append(
                {
                    "id": cid,
                    "shard_id": shard,
                    "bytes_raw_utf8": br,
                    "bytes_compressed_utf8": bc,
                    "exact_match": True,
                    "segment_count_sm": 0,
                    "segment_count_merged": 0,
                    "payload_bytes": 0,
                    "framing_bytes_varint4": 0,
                    "total_wire_bytes": int(wire),
                    "real_saving_vs_raw": 1.0 - (wire / float(br)),
                }
            )
            sum_raw += br
            sum_comp += bc
            sum_wire += wire
            n_included += 1
            continue

        payload, raw_n, n_merged, merged, framing = analyze_case(
            raw_b,
            rec_b,
            merge_gap_bytes=int(args.merge_gap_bytes),
        )
        wire = float(bc + payload + framing)
        rows.append(
            {
                "id": cid,
                "shard_id": shard,
                "bytes_raw_utf8": br,
                "bytes_compressed_utf8": bc,
                "exact_match": False,
                "segment_count_sm_non_equal": raw_n,
                "segment_count_merged": n_merged,
                "payload_bytes": payload,
                "framing_bytes_varint4": framing,
                "merge_gap_bytes": int(args.merge_gap_bytes),
                "total_wire_bytes": int(wire),
                "real_saving_vs_raw": 1.0 - (wire / float(br)),
            }
        )
        sum_raw += br
        sum_comp += bc
        sum_wire += wire
        n_included += 1

    gsave = 1.0 - (sum_wire / sum_raw) if sum_raw else 0.0

    payload = {
        "schema": "integrity_cost_model_v4",
        "description": (
            "Merged opcode segments (small equal gaps absorbed) + varint4 framing estimate. "
            "Does not include encryption, checksums, or chunk headers."
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_report": str(rep_path.relative_to(ROOT)).replace("\\", "/"),
        "source_input": str(inp_path.relative_to(ROOT)).replace("\\", "/"),
        "run_config_snapshot": run_cfg,
        "v4_config": {
            "merge_gap_bytes": int(args.merge_gap_bytes),
            "shard_id_filter": shard_filter,
        },
        "summary": {
            "cases_included": n_included,
            "bytes_raw_total": int(sum_raw),
            "bytes_compressed_total": int(sum_comp),
            "total_wire_bytes": int(sum_wire),
            "global_real_saving_vs_raw": gsave,
            "global_token_saving_rate_reported": float(cm.get("global_token_saving_rate") or 0.0)
            if not shard_filter
            else None,
        },
        "cases": rows,
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {out_path} cases={n_included} real_saving={gsave:.4f} gap={args.merge_gap_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
