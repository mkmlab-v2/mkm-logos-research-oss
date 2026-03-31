# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.84, L:0.88, K:0.41, M:0.46}
# Balance: 89
# Purpose: Convert B-track eval JSONL rows into sasang clinical evaluator prediction schema.
# Keywords: btrack, sasang, converter, jsonl, predictions
#!/usr/bin/env python3
"""Convert B-track eval JSONL to sasang prediction JSONL schema.

Output schema per line:
{
  "sample_id": "...",
  "predicted_parent": "TY|SY|TE|SE",
  "confidence": 0.0-1.0,
  "prediction_source": "..."
}

Conversion precedence:
1) If row has predicted_parent already -> use it.
2) Else if --state-map provided and row has state_id -> map state_id -> parent.
3) Else map row.direction via --direction-map (default: up->SY, down->TE, flat->SE).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PARENTS = {"TY", "SY", "TE", "SE"}
DEFAULT_DIRECTION_MAP = {"up": "SY", "down": "TE", "flat": "SE"}


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _safe_float(value: Any, fallback: float = 0.5) -> float:
    if isinstance(value, (int, float)):
        v = float(value)
    elif isinstance(value, str):
        try:
            v = float(value)
        except ValueError:
            v = fallback
    else:
        v = fallback
    return max(0.0, min(1.0, v))


def _load_state_map(path: Path | None) -> dict[int, str]:
    if path is None:
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    # Expected shape:
    # {"13":"TY", "8":"SY", ...} or {"state_to_parent":{"13":"TY",...}}
    raw = doc.get("state_to_parent", doc)
    out: dict[int, str] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            try:
                sid = int(k)
            except (TypeError, ValueError):
                continue
            parent = str(v).strip().upper()
            if parent in PARENTS:
                out[sid] = parent
    return out


def _predicted_parent(
    row: dict[str, Any],
    *,
    direction_map: dict[str, str],
    state_map: dict[int, str],
    fallback_parent: str,
) -> str:
    direct = str(row.get("predicted_parent", "")).strip().upper()
    if direct in PARENTS:
        return direct

    sid = row.get("state_id")
    if isinstance(sid, int) and sid in state_map:
        return state_map[sid]
    if isinstance(sid, str):
        try:
            sid_i = int(sid)
            if sid_i in state_map:
                return state_map[sid_i]
        except ValueError:
            pass

    direction = str(row.get("direction", "")).strip().lower()
    mapped = direction_map.get(direction, fallback_parent).strip().upper()
    return mapped if mapped in PARENTS else fallback_parent


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert B-track eval JSONL to sasang prediction JSONL schema.")
    ap.add_argument("--input", required=True, help="Input JSONL path (e.g., data/logos/btrack_pilot/bench/b_track_eval.jsonl)")
    ap.add_argument(
        "--out",
        default="reports/constitution/btrack_pilot/sasang_predictions_from_btrack_latest.jsonl",
        help="Output JSONL path",
    )
    ap.add_argument("--sample-id-key", default="id", help="Row key used as sample_id")
    ap.add_argument(
        "--direction-map",
        default=json.dumps(DEFAULT_DIRECTION_MAP),
        help='JSON string mapping direction to parent, e.g. {"up":"SY","down":"TE","flat":"SE"}',
    )
    ap.add_argument(
        "--state-map",
        default="",
        help="Optional JSON file mapping state_id to parent",
    )
    ap.add_argument("--fallback-parent", default="TY", choices=sorted(PARENTS))
    ap.add_argument("--source-tag", default="btrack_eval_converter_v1")
    args = ap.parse_args()

    in_path = _abs(args.input)
    out_path = _abs(args.out)
    if not in_path.is_file():
        print(f"ERROR: missing input file: {in_path}")
        return 2

    try:
        direction_map_raw = json.loads(args.direction_map)
        direction_map = {str(k).strip().lower(): str(v).strip().upper() for k, v in direction_map_raw.items()}
    except Exception as e:  # pragma: no cover - CLI error path
        print(f"ERROR: invalid --direction-map JSON: {e}")
        return 2

    state_map_path = _abs(args.state_map) if args.state_map else None
    if state_map_path and not state_map_path.is_file():
        print(f"ERROR: missing --state-map file: {state_map_path}")
        return 2
    state_map = _load_state_map(state_map_path)

    rows = _load_jsonl(in_path)
    out_rows: list[dict[str, Any]] = []
    skipped = 0
    for i, row in enumerate(rows, 1):
        sid_raw = row.get(args.sample_id_key)
        sample_id = str(sid_raw).strip() if sid_raw is not None else ""
        if not sample_id:
            sample_id = f"row_{i:08d}"
        parent = _predicted_parent(
            row,
            direction_map=direction_map,
            state_map=state_map,
            fallback_parent=args.fallback_parent,
        )
        if parent not in PARENTS:
            skipped += 1
            continue
        out_rows.append(
            {
                "sample_id": sample_id,
                "predicted_parent": parent,
                "confidence": _safe_float(row.get("confidence"), fallback=0.5),
                "prediction_source": args.source_tag,
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out_rows), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "input_rows": len(rows),
                "written_rows": len(out_rows),
                "skipped_rows": skipped,
                "output_path": str(out_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

