#!/usr/bin/env python3
"""Aggregate INTEGRITY_COST_V2 per-case opcode metrics by shard_id (byte-weighted)."""

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

DEFAULT_V2 = ROOT / "docs" / "final" / "artifacts" / "INTEGRITY_COST_V2_UNIVERSAL_V1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "SHARD_OPCODE_PROFIT_V1.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Shard-level opcode profit from integrity v2 JSON.")
    ap.add_argument("--v2-json", type=Path, default=DEFAULT_V2)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    p = Path(args.v2_json).resolve()
    if not p.is_file():
        print(f"FAIL: not found {p}", file=sys.stderr)
        return 1

    doc = json.loads(p.read_text(encoding="utf-8"))
    cases = doc.get("cases") or []

    by_shard: dict[str, dict[str, float]] = {}
    for c in cases:
        sh = str(c.get("shard_id") or "_no_route_")
        br = float(c.get("bytes_raw_utf8") or 0)
        tw = float(c.get("total_wire_opcode") or 0)
        if br <= 0:
            continue
        if sh not in by_shard:
            by_shard[sh] = {"bytes_raw": 0.0, "total_wire_opcode": 0.0, "n": 0}
        by_shard[sh]["bytes_raw"] += br
        by_shard[sh]["total_wire_opcode"] += tw
        by_shard[sh]["n"] += 1

    rows: list[dict[str, Any]] = []
    for sh, agg in sorted(by_shard.items(), key=lambda x: -x[1]["bytes_raw"]):
        br = agg["bytes_raw"]
        tw = agg["total_wire_opcode"]
        sav = 1.0 - (tw / br) if br else 0.0
        rows.append(
            {
                "shard_id": sh,
                "case_count": int(agg["n"]),
                "bytes_raw_total": int(br),
                "total_wire_opcode_bytes": int(tw),
                "byte_weighted_real_saving_vs_raw_opcode": sav,
            }
        )

    rows.sort(key=lambda r: r["byte_weighted_real_saving_vs_raw_opcode"], reverse=True)

    out_doc = {
        "schema": "shard_opcode_profit_v1",
        "description": "Byte-weighted real saving (opcode model) per shard from INTEGRITY_COST_V2 cases.",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_v2": str(p.relative_to(ROOT)).replace("\\", "/"),
        "shards_ranked_by_opcode_profit": rows,
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    top = rows[0]["shard_id"] if rows else ""
    print(f"OK: wrote {out_path} top_shard={top}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
