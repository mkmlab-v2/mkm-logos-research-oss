#!/usr/bin/env python3
"""Apply anchor evidence boosts to B-track recalibrated rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IN_B = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "b_track_eval_recalibrated_v2.jsonl"
SLOTS = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "btrack_anchor_evidence_slots.jsonl"
OUT_B = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "b_track_eval_anchor_applied.jsonl"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply anchor evidence boosts to B-track rows")
    ap.add_argument("--in-b", default=str(IN_B))
    ap.add_argument("--slots", default=str(SLOTS))
    ap.add_argument("--out-b", default=str(OUT_B))
    args = ap.parse_args()

    in_b = _abs(args.in_b)
    slots = _abs(args.slots)
    out_b = _abs(args.out_b)
    if not in_b.is_file():
        print(f"ERROR: missing B-track file: {in_b}")
        return 2
    if not slots.is_file():
        print(f"ERROR: missing anchor slots file: {slots}")
        return 2

    b_rows = _load_jsonl(in_b)
    slot_rows = _load_jsonl(slots)
    by_key: dict[str, dict[str, Any]] = {}
    for s in slot_rows:
        key = str(s.get("key", ""))
        if key:
            by_key[key] = s

    updated = 0
    out_rows: list[dict[str, Any]] = []
    for r in b_rows:
        row = dict(r)
        key = str(row.get("id", ""))
        slot = by_key.get(key)
        if slot:
            cb = slot.get("confidence_boost", 0.0)
            sb = slot.get("snr_boost", 0.0)
            if isinstance(cb, (int, float)) and isinstance(sb, (int, float)):
                c = row.get("confidence")
                s = row.get("snr")
                if isinstance(c, (int, float)) and isinstance(s, (int, float)):
                    row["confidence"] = round(_clamp(float(c) + float(cb), 0.0, 0.96), 6)
                    row["snr"] = round(_clamp(float(s) + float(sb), 0.6, 1.5), 6)
                    row["anchor_evidence_applied"] = True
                    row["anchor_status"] = slot.get("anchor_status", "unknown")
                    row["anchor_strength"] = slot.get("anchor_strength")
                    updated += 1
        out_rows.append(row)

    out_b.parent.mkdir(parents=True, exist_ok=True)
    with out_b.open("w", encoding="utf-8") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("OK: anchor evidence applied")
    print(f"out={out_b}")
    print(f"updated_rows={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
