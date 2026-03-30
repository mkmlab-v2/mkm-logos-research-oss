#!/usr/bin/env python3
"""Diagnose B-Track hold decision and emit remediation candidates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DETAILS = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_pair_details_latest.jsonl"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_hold_diagnosis_latest.json"


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
    ap = argparse.ArgumentParser(description="Diagnose B-Track hold from pair details")
    ap.add_argument("--details", default=str(DETAILS))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    details_path = _abs(args.details)
    out_path = _abs(args.out)
    if not details_path.is_file():
        print(f"ERROR: missing details file: {details_path}")
        return 2

    rows = _load_jsonl(details_path)
    if not rows:
        print("ERROR: empty details rows")
        return 3

    def cdelta(r: dict[str, Any]) -> float:
        v = r.get("confidence_delta_b_minus_a")
        return float(v) if isinstance(v, (int, float)) else -999.0

    def sdelta(r: dict[str, Any]) -> float:
        v = r.get("snr_delta_b_minus_a")
        return float(v) if isinstance(v, (int, float)) else -999.0

    worst_conf = sorted(rows, key=cdelta)[:5]
    worst_snr = sorted(rows, key=sdelta)[:5]
    stable = [
        r for r in rows
        if isinstance(r.get("confidence_delta_b_minus_a"), (int, float))
        and isinstance(r.get("snr_delta_b_minus_a"), (int, float))
        and float(r["confidence_delta_b_minus_a"]) >= -0.08
        and float(r["snr_delta_b_minus_a"]) >= -0.06
    ]

    diagnosis = {
        "schema": "btrack_hold_diagnosis_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_details": str(details_path),
        "counts": {
            "total_pairs": len(rows),
            "stable_near_zero_pairs": len(stable),
        },
        "worst_confidence_deltas": [
            {"key": r.get("key"), "delta": r.get("confidence_delta_b_minus_a")} for r in worst_conf
        ],
        "worst_snr_deltas": [
            {"key": r.get("key"), "delta": r.get("snr_delta_b_minus_a")} for r in worst_snr
        ],
        "remediation": [
            "Prioritize satellite anchor upgrades for worst 5 states before promotion.",
            "Keep A-track frozen; run state-specific recalibration only on B-track.",
            "Re-run gate after anchor and confidence calibration updates.",
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(diagnosis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: diagnosis report written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
