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
OUT_DEFAULT = ART / "genesis_sequence_net_efficiency_model_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep-json", type=Path, default=SWEEP_DEFAULT)
    ap.add_argument("--nodes", type=int, default=20, help="Number of receiver nodes sharing codebook sync cost.")
    ap.add_argument(
        "--daily-sync-bytes",
        type=int,
        default=10485760,
        help="Daily codebook sync cost in bytes (default 10 MiB).",
    )
    ap.add_argument(
        "--daily-message-count",
        type=int,
        default=200000,
        help="Daily number of compressed messages sharing sync cost.",
    )
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    sweep_path = args.sweep_json if args.sweep_json.is_absolute() else ROOT / args.sweep_json
    sweep = _read_json(sweep_path)
    rows = sweep.get("rows", [])

    nodes = max(1, int(args.nodes))
    per_msg_sync_cost = _safe_div(float(args.daily_sync_bytes), float(max(1, args.daily_message_count) * nodes))

    out_rows: list[dict[str, Any]] = []
    ptr_break_even_net: int | None = None
    vec_break_even_net: int | None = None
    for row in rows:
        avg_raw = float(row.get("avg_raw_utf8_bytes", 0.0))
        ptr_payload = float(row.get("pointer_payload_bytes", 8.0))
        vec_payload = float(row.get("vector4_payload_bytes", 16.0))

        ptr_net_payload = ptr_payload + per_msg_sync_cost
        vec_net_payload = vec_payload + per_msg_sync_cost
        ptr_net_saving = 1.0 - _safe_div(ptr_net_payload, max(1.0, avg_raw))
        vec_net_saving = 1.0 - _safe_div(vec_net_payload, max(1.0, avg_raw))

        out_row = {
            "target_length_chars": int(row.get("target_length_chars", 0)),
            "avg_raw_utf8_bytes": avg_raw,
            "pointer_payload_bytes": ptr_payload,
            "vector4_payload_bytes": vec_payload,
            "amortized_sync_bytes_per_message": per_msg_sync_cost,
            "pointer_net_payload_bytes": ptr_net_payload,
            "vector4_net_payload_bytes": vec_net_payload,
            "pointer_net_saving_rate": ptr_net_saving,
            "vector4_net_saving_rate": vec_net_saving,
        }
        out_rows.append(out_row)
        if ptr_break_even_net is None and ptr_net_saving > 0.0:
            ptr_break_even_net = out_row["target_length_chars"]
        if vec_break_even_net is None and vec_net_saving > 0.0:
            vec_break_even_net = out_row["target_length_chars"]

    doc = {
        "schema": "genesis_sequence_net_efficiency_model_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "inputs": {
            "sweep_json": str(sweep_path),
            "nodes": nodes,
            "daily_sync_bytes": int(args.daily_sync_bytes),
            "daily_message_count": int(args.daily_message_count),
        },
        "model": {
            "amortized_sync_bytes_per_message": per_msg_sync_cost,
            "assumption": "sync cost is evenly amortized across all daily messages and nodes",
        },
        "rows": out_rows,
        "summary": {
            "pointer_net_break_even_length_chars": ptr_break_even_net,
            "vector4_net_break_even_length_chars": vec_break_even_net,
        },
        "notes": [
            "Model-based estimate only; real ops depends on churn rate, cache hit, and rollout cadence.",
            "This includes sync overhead amortization but excludes operational retries and failure traffic.",
        ],
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "summary": doc["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
