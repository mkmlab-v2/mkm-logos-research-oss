#!/usr/bin/env python3
"""Build candidate-for-promotion subset from recalibrated pair details."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.myeongni.btrack_bench_paths import CANONICAL_A_TRACK_EVAL

DETAILS = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_pair_details_recalibrated_latest.jsonl"
A_IN = ROOT / CANONICAL_A_TRACK_EVAL
B_IN = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "b_track_eval_recalibrated.jsonl"
A_OUT = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "a_track_eval_candidate_subset.jsonl"
B_OUT = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "b_track_eval_candidate_subset.jsonl"


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
    ap = argparse.ArgumentParser(description="Build candidate subset from recalibrated details")
    ap.add_argument("--details", default=str(DETAILS))
    ap.add_argument("--a-in", default=str(A_IN))
    ap.add_argument("--b-in", default=str(B_IN))
    ap.add_argument("--a-out", default=str(A_OUT))
    ap.add_argument("--b-out", default=str(B_OUT))
    ap.add_argument("--max-conf-drop", type=float, default=0.08)
    ap.add_argument("--max-snr-drop", type=float, default=0.06)
    args = ap.parse_args()

    details = _load_jsonl(_abs(args.details))
    a_rows = _load_jsonl(_abs(args.a_in))
    b_rows = _load_jsonl(_abs(args.b_in))

    candidate_ids: set[str] = set()
    for r in details:
        key = str(r.get("key", ""))
        cd = r.get("confidence_delta_b_minus_a")
        sd = r.get("snr_delta_b_minus_a")
        if not isinstance(cd, (int, float)) or not isinstance(sd, (int, float)):
            continue
        if float(cd) >= -abs(args.max_conf_drop) and float(sd) >= -abs(args.max_snr_drop):
            candidate_ids.add(key)

    if not candidate_ids:
        print("ERROR: no candidate states matched thresholds")
        return 3

    a_out_rows = [r for r in a_rows if str(r.get("id", "")) in candidate_ids]
    b_out_rows = [r for r in b_rows if str(r.get("id", "")) in candidate_ids]

    a_out = _abs(args.a_out)
    b_out = _abs(args.b_out)
    a_out.parent.mkdir(parents=True, exist_ok=True)
    b_out.parent.mkdir(parents=True, exist_ok=True)
    with a_out.open("w", encoding="utf-8") as fa:
        for r in a_out_rows:
            fa.write(json.dumps(r, ensure_ascii=False) + "\n")
    with b_out.open("w", encoding="utf-8") as fb:
        for r in b_out_rows:
            fb.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("OK: candidate subset generated")
    print(f"candidate_count={len(candidate_ids)}")
    print(f"a_out={a_out}")
    print(f"b_out={b_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
