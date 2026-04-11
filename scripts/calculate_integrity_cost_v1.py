#!/usr/bin/env python3
"""Estimate wire cost when exact-match requires a side channel carrying full raw UTF-8.

Model v1 (conservative upper bound):
  - Primary channel: compressed_text_effective (UTF-8 bytes).
  - If raw != reconstructed: add side_channel_bytes = len(raw UTF-8) (literal oracle / hard-insertion).
  - If raw == reconstructed: side channel 0.

Total wire bytes per case = bytes_comp + side_bytes.
Reported token_saving_rate from MULTILENS is word-token proxy; this script uses UTF-8 byte counts
for a single comparable "wire" story (see note in output).

Real saving vs sending uncompressed raw only:
  real_saving_vs_raw = 1 - (total_wire_bytes / bytes_raw)
Per-case this can be negative when bytes_comp + bytes_raw > bytes_raw.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_V2_UNIVERSAL_SHARD_PROBE_V1.json"
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "INTEGRITY_COST_UNIVERSAL_V1.json"


def _b(s: str) -> int:
    return len(s.encode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Integrity-adjusted wire cost (full-raw side channel model v1).")
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
    sum_raw = 0
    sum_comp = 0
    sum_side = 0
    sum_wire = 0
    mismatch_n = 0
    shard_side: dict[str, float] = defaultdict(float)
    shard_raw: dict[str, int] = defaultdict(int)

    for row in cases:
        cid = str(row.get("id", ""))
        raw = raw_by_id.get(cid, "")
        rec = str(row.get("reconstructed_text_effective", ""))
        comp = str(row.get("compressed_text_effective", ""))
        route = row.get("route") if isinstance(row.get("route"), dict) else {}
        shard = str(route.get("shard_id") or "_no_route_")

        br = _b(raw)
        bc = _b(comp)
        mismatch = raw != rec
        side = float(br) if mismatch else 0.0
        wire = bc + side

        if br <= 0:
            continue

        sum_raw += br
        sum_comp += bc
        sum_side += side
        sum_wire += wire
        if mismatch:
            mismatch_n += 1
        shard_side[shard] += side
        shard_raw[shard] += br

        rows_out.append(
            {
                "id": cid,
                "shard_id": shard,
                "bytes_raw_utf8": br,
                "bytes_compressed_utf8": bc,
                "exact_match_without_side": not mismatch,
                "side_channel_bytes_full_raw_model": int(side),
                "total_wire_bytes": int(wire),
                "real_saving_vs_raw": 1.0 - (wire / float(br)),
                "reported_token_saving_rate": row.get("token_saving_rate"),
            }
        )

    global_reported = float(cm.get("global_token_saving_rate") or 0.0)
    global_real = 1.0 - (sum_wire / float(sum_raw)) if sum_raw else 0.0
    global_naive_comp_only = 1.0 - (float(sum_comp) / float(sum_raw)) if sum_raw else 0.0

    by_shard: dict[str, Any] = {}
    for sh in sorted(shard_raw.keys()):
        brs = float(shard_raw[sh])
        ss = shard_side[sh]
        # approximate wire for shard: need sum_comp per shard - compute in second pass
        by_shard[sh] = {
            "bytes_raw_total": int(shard_raw[sh]),
            "side_channel_bytes_total": int(ss),
            "mismatch_fraction_of_raw_weighted": ss / brs if brs else 0.0,
        }

    # second pass for per-shard compressed sum
    sc_sum: dict[str, int] = defaultdict(int)
    for row in cases:
        cid = str(row.get("id", ""))
        raw = raw_by_id.get(cid, "")
        if not raw:
            continue
        comp = str(row.get("compressed_text_effective", ""))
        route = row.get("route") if isinstance(row.get("route"), dict) else {}
        shard = str(route.get("shard_id") or "_no_route_")
        sc_sum[shard] += _b(comp)

    for sh in by_shard:
        brs = float(shard_raw[sh])
        csum = float(sc_sum.get(sh, 0))
        wsum = csum + shard_side[sh]
        by_shard[sh]["bytes_compressed_total"] = int(csum)
        by_shard[sh]["total_wire_bytes"] = int(wsum)
        by_shard[sh]["real_saving_vs_raw"] = 1.0 - (wsum / brs) if brs else 0.0

    payload = {
        "schema": "integrity_cost_model_v1",
        "description": (
            "Full-raw side channel when reconstructed != raw. "
            "Upper bound: actual diff patches could be smaller. "
            "Token metrics in MULTILENS differ from UTF-8 byte accounting."
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_report": str(rep_path.relative_to(ROOT)).replace("\\", "/"),
        "source_input": str(inp_path.relative_to(ROOT)).replace("\\", "/"),
        "run_config_snapshot": run_cfg,
        "summary": {
            "case_count": len(rows_out),
            "mismatch_count_raw_ne_rec": mismatch_n,
            "bytes_raw_total": int(sum_raw),
            "bytes_compressed_total": int(sum_comp),
            "side_channel_bytes_total_full_raw_model": int(sum_side),
            "total_wire_bytes": int(sum_wire),
            "global_token_saving_rate_reported": global_reported,
            "global_saving_vs_raw_compressed_only_naive_bytes": global_naive_comp_only,
            "global_real_saving_vs_raw_bytes_integrity_adjusted": global_real,
        },
        "by_shard": by_shard,
        "cases": rows_out,
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"OK: wrote {out_path} real_saving={global_real:.4f} "
        f"(reported_token={global_reported:.4f}, mismatches={mismatch_n}/{len(rows_out)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
