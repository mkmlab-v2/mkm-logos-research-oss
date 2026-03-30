#!/usr/bin/env python3
"""Initialize anchor evidence slots for hold-state recalibration."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DETAILS = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_pair_details_recalibrated_v2_latest.jsonl"
OUT = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "btrack_anchor_evidence_slots.jsonl"


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
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Initialize anchor evidence slots for hold states")
    ap.add_argument("--details", default=str(DETAILS))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--conf-threshold", type=float, default=-0.01, help="States below this delta are treated as hold")
    ap.add_argument("--snr-threshold", type=float, default=-0.01, help="States below this delta are treated as hold")
    args = ap.parse_args()

    details_path = _abs(args.details)
    out_path = _abs(args.out)
    if not details_path.is_file():
        print(f"ERROR: missing details file: {details_path}")
        return 2

    details = _load_jsonl(details_path)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    slots: list[dict[str, Any]] = []
    for r in details:
        key = str(r.get("key", ""))
        if not key.startswith("STATE_"):
            continue
        try:
            state_id = int(key.split("_")[1])
        except (ValueError, IndexError):
            continue
        cdelta = r.get("confidence_delta_b_minus_a")
        sdelta = r.get("snr_delta_b_minus_a")
        if not isinstance(cdelta, (int, float)) or not isinstance(sdelta, (int, float)):
            continue
        if float(cdelta) >= args.conf_threshold and float(sdelta) >= args.snr_threshold:
            continue

        # Provisional defaults; replace after real anchor curation.
        slots.append(
            {
                "state_id": state_id,
                "key": key,
                "anchor_status": "provisional",
                "anchor_strength": 0.7,
                "confidence_boost": 0.03,
                "snr_boost": 0.03,
                "evidence_ref": "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json",
                "updated_at_utc": ts,
                "note": "Auto-seeded slot for hold-state remediation; replace with verified anchor evidence.",
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in slots:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("OK: anchor evidence slots initialized")
    print(f"out={out_path}")
    print(f"slot_count={len(slots)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
