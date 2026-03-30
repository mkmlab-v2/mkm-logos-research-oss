#!/usr/bin/env python3
"""Second-pass recalibration for hold states only.

Policy:
- Keep near-stable states unchanged.
- For hold states, lift B so deltas are floored at configurable bounds.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DETAILS = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_pair_details_recalibrated_latest.jsonl"
A_IN = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "a_track_eval.jsonl"
B_IN = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "b_track_eval_recalibrated.jsonl"
B_OUT = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "b_track_eval_recalibrated_v2.jsonl"


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
    ap = argparse.ArgumentParser(description="Second-pass recalibration for hold states")
    ap.add_argument("--details", default=str(DETAILS))
    ap.add_argument("--a-in", default=str(A_IN))
    ap.add_argument("--b-in", default=str(B_IN))
    ap.add_argument("--b-out", default=str(B_OUT))
    ap.add_argument("--conf-floor-delta", type=float, default=-0.03)
    ap.add_argument("--snr-floor-delta", type=float, default=-0.03)
    ap.add_argument("--stable-conf-delta", type=float, default=-0.08)
    ap.add_argument("--stable-snr-delta", type=float, default=-0.06)
    args = ap.parse_args()

    details_rows = _load_jsonl(_abs(args.details))
    a_rows = _load_jsonl(_abs(args.a_in))
    b_rows = _load_jsonl(_abs(args.b_in))

    a_by_id = {str(r.get("id", "")): r for r in a_rows}
    b_by_id = {str(r.get("id", "")): dict(r) for r in b_rows}

    stable_ids: set[str] = set()
    for r in details_rows:
        key = str(r.get("key", ""))
        cd = r.get("confidence_delta_b_minus_a")
        sd = r.get("snr_delta_b_minus_a")
        if isinstance(cd, (int, float)) and isinstance(sd, (int, float)):
            if float(cd) >= args.stable_conf_delta and float(sd) >= args.stable_snr_delta:
                stable_ids.add(key)

    updated = 0
    for key, b in b_by_id.items():
        if key in stable_ids:
            continue
        a = a_by_id.get(key)
        if not a:
            continue
        a_conf = a.get("confidence")
        a_snr = a.get("snr")
        b_conf = b.get("confidence")
        b_snr = b.get("snr")
        if not all(isinstance(x, (int, float)) for x in (a_conf, a_snr, b_conf, b_snr)):
            continue

        min_conf = float(a_conf) + args.conf_floor_delta
        min_snr = float(a_snr) + args.snr_floor_delta
        new_conf = _clamp(max(float(b_conf), min_conf), 0.0, 0.95)
        new_snr = _clamp(max(float(b_snr), min_snr), 0.6, 1.5)

        if new_conf != float(b_conf) or new_snr != float(b_snr):
            b["confidence"] = round(new_conf, 6)
            b["snr"] = round(new_snr, 6)
            b["recalibrated_v2"] = True
            b["recalibration_policy_v2"] = "hold_states_floor_delta"
            updated += 1

    out_rows = [b_by_id[str(r.get("id", ""))] for r in b_rows if str(r.get("id", "")) in b_by_id]
    out_path = _abs(args.b_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("OK: hold-state recalibration v2 written")
    print(f"updated_rows={updated}")
    print(f"stable_rows={len(stable_ids)}")
    print(f"out={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
