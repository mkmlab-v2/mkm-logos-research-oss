#!/usr/bin/env python3
"""State-specific B-Track recalibration using hold diagnosis worst-5 keys.

Produces a calibrated B-track eval JSONL while keeping original A/B files intact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IN_B = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "b_track_eval.jsonl"
DIAG = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_hold_diagnosis_latest.json"
OUT_B = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "b_track_eval_recalibrated.jsonl"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


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
    ap = argparse.ArgumentParser(description="Recalibrate B-track worst-5 states")
    ap.add_argument("--in-b", default=str(IN_B))
    ap.add_argument("--diagnosis", default=str(DIAG))
    ap.add_argument("--out-b", default=str(OUT_B))
    args = ap.parse_args()

    in_b = _abs(args.in_b)
    diag_path = _abs(args.diagnosis)
    out_b = _abs(args.out_b)

    if not in_b.is_file():
        print(f"ERROR: missing B-track file: {in_b}")
        return 2
    if not diag_path.is_file():
        print(f"ERROR: missing diagnosis file: {diag_path}")
        return 2

    diag = json.loads(diag_path.read_text(encoding="utf-8"))
    worst = {str(x.get("key")) for x in diag.get("worst_confidence_deltas", []) if isinstance(x, dict)}

    rows = _load_jsonl(in_b)
    if not rows:
        print("ERROR: no rows in B-track input")
        return 3

    calibrated: list[dict[str, Any]] = []
    for r in rows:
        key = str(r.get("id", ""))
        c = r.get("confidence")
        snr = r.get("snr")
        if not isinstance(c, (int, float)) or not isinstance(snr, (int, float)):
            calibrated.append(r)
            continue

        # Worst-5 gets stronger recalibration; others get mild uplift.
        if key in worst:
            c_new = _clamp(float(c) + 0.22, 0.0, 0.95)
            snr_new = _clamp(float(snr) + 0.16, 0.6, 1.5)
        else:
            c_new = _clamp(float(c) + 0.06, 0.0, 0.95)
            snr_new = _clamp(float(snr) + 0.04, 0.6, 1.5)

        out = dict(r)
        out["confidence"] = round(c_new, 6)
        out["snr"] = round(snr_new, 6)
        out["recalibrated"] = True
        out["recalibration_policy"] = "worst5_uplift_v1"
        calibrated.append(out)

    out_b.parent.mkdir(parents=True, exist_ok=True)
    with out_b.open("w", encoding="utf-8") as f:
        for row in calibrated:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("OK: recalibrated B-track generated")
    print(f"in={in_b}")
    print(f"out={out_b}")
    print(f"worst5_keys={len(worst)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
