#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
SWEEP_DEFAULT = ART / "genesis_sequence_compression_sweep_latest.json"
OUT_DEFAULT = ART / "genesis_sequence_net_efficiency_sensitivity_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _parse_int_csv(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not vals:
        raise ValueError("empty csv list")
    return vals


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep-json", type=Path, default=SWEEP_DEFAULT)
    ap.add_argument("--nodes-csv", type=str, default="1,5,20,50")
    ap.add_argument("--daily-sync-bytes-csv", type=str, default="1048576,10485760,52428800")
    ap.add_argument("--daily-message-count-csv", type=str, default="50000,200000,1000000")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    sweep_path = args.sweep_json if args.sweep_json.is_absolute() else ROOT / args.sweep_json
    sweep = _read_json(sweep_path)
    rows = sweep.get("rows", [])

    nodes_list = _parse_int_csv(args.nodes_csv)
    sync_list = _parse_int_csv(args.daily_sync_bytes_csv)
    msg_list = _parse_int_csv(args.daily_message_count_csv)

    scenarios: list[dict[str, Any]] = []
    for nodes in nodes_list:
        for sync_bytes in sync_list:
            for msg_count in msg_list:
                amortized = _safe_div(float(sync_bytes), float(max(1, nodes) * max(1, msg_count)))
                ptr_break = None
                vec_break = None
                ptr_400 = None
                for r in rows:
                    raw = float(r["avg_raw_utf8_bytes"])
                    ptr_net = 1.0 - _safe_div(float(r["pointer_payload_bytes"]) + amortized, max(1.0, raw))
                    vec_net = 1.0 - _safe_div(float(r["vector4_payload_bytes"]) + amortized, max(1.0, raw))
                    if ptr_break is None and ptr_net > 0.0:
                        ptr_break = int(r["target_length_chars"])
                    if vec_break is None and vec_net > 0.0:
                        vec_break = int(r["target_length_chars"])
                    if int(r["target_length_chars"]) == 400:
                        ptr_400 = ptr_net
                scenarios.append(
                    {
                        "nodes": nodes,
                        "daily_sync_bytes": sync_bytes,
                        "daily_message_count": msg_count,
                        "amortized_sync_bytes_per_message": amortized,
                        "pointer_net_break_even_length_chars": ptr_break,
                        "vector4_net_break_even_length_chars": vec_break,
                        "pointer_net_saving_rate_at_400_chars": ptr_400,
                    }
                )

    # "99% zone" where pointer net saving at 400 chars >= 0.99
    zone_99 = [
        s
        for s in scenarios
        if s["pointer_net_saving_rate_at_400_chars"] is not None and s["pointer_net_saving_rate_at_400_chars"] >= 0.99
    ]

    out_doc = {
        "schema": "genesis_sequence_net_efficiency_sensitivity_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "inputs": {
            "sweep_json": str(sweep_path),
            "nodes_csv": nodes_list,
            "daily_sync_bytes_csv": sync_list,
            "daily_message_count_csv": msg_list,
        },
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "summary": {
            "pointer_99pct_zone_count": len(zone_99),
            "pointer_99pct_zone_sample": zone_99[:5],
            "note": "99% zone uses pointer_net_saving_rate_at_400_chars >= 0.99 criterion.",
        },
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(out_path), "scenario_count": len(scenarios), "pointer_99pct_zone_count": len(zone_99)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
