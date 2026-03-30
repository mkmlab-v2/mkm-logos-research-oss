#!/usr/bin/env python3
"""Build A/B bench from direct in-workspace logs (no synthetic uplift model).

A-track source:
  data/myeongni/myeongni_16_state_audit_v1.jsonl
    - uses per-state observed confidence from consistency_rate / audit.confidence_score

B-track source:
  data/myeongni/myeongni_16_state_experiment_20260329.jsonl
    - uses per-state observed 4D vector; converts to confidence via distance to 0.25 centroid
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
AUDIT_LOG = ROOT / "data" / "myeongni" / "myeongni_16_state_audit_v1.jsonl"
BTRACK_LOG = ROOT / "data" / "myeongni" / "myeongni_16_state_experiment_20260329.jsonl"
A_OUT = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "a_track_eval.jsonl"
B_OUT = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "b_track_eval.jsonl"


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


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _direction(state_id: int) -> str:
    if state_id <= 5:
        return "up"
    if state_id <= 11:
        return "flat"
    return "down"


def _centroid_confidence(v4: dict[str, Any]) -> float | None:
    keys = ("S", "L", "K", "M")
    if not all(k in v4 for k in keys):
        return None
    vals: list[float] = []
    for k in keys:
        x = v4.get(k)
        if not isinstance(x, (int, float)):
            return None
        vals.append(float(x))
    # Convert Euclidean distance to confidence-like score in [0,1].
    # max_dist is from centroid(0.25) to corner (1,1,1,1): sqrt(4*0.75^2)=1.5
    d = math.sqrt(sum((x - 0.25) ** 2 for x in vals))
    max_dist = 1.5
    return _clamp(1.0 - (d / max_dist), 0.0, 1.0)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build A/B bench from direct logs")
    ap.add_argument("--audit-log", default=str(AUDIT_LOG))
    ap.add_argument("--btrack-log", default=str(BTRACK_LOG))
    ap.add_argument("--a-out", default=str(A_OUT))
    ap.add_argument("--b-out", default=str(B_OUT))
    args = ap.parse_args()

    audit_path = _abs(args.audit_log)
    btrack_path = _abs(args.btrack_log)
    a_out = _abs(args.a_out)
    b_out = _abs(args.b_out)

    if not audit_path.is_file():
        print(f"ERROR: missing audit log: {audit_path}")
        return 2
    if not btrack_path.is_file():
        print(f"ERROR: missing btrack log: {btrack_path}")
        return 2

    audit_rows = _load_jsonl(audit_path)
    btrack_rows = _load_jsonl(btrack_path)

    a_by_state: dict[int, float] = {}
    for r in audit_rows:
        sid = r.get("state_id")
        if not isinstance(sid, int):
            continue
        c = r.get("consistency_rate")
        if not isinstance(c, (int, float)):
            audit = r.get("audit")
            if isinstance(audit, dict):
                c = audit.get("confidence_score")
        if isinstance(c, (int, float)):
            a_by_state[sid] = _clamp(float(c), 0.0, 1.0)

    b_by_state: dict[int, float] = {}
    for r in btrack_rows:
        sid = r.get("state_id")
        if not isinstance(sid, int):
            continue
        v4 = r.get("vector_4d")
        if not isinstance(v4, dict):
            continue
        c = _centroid_confidence(v4)
        if c is not None:
            b_by_state[sid] = c

    states = sorted(set(a_by_state) & set(b_by_state))
    if not states:
        print("ERROR: no overlapping state_id between A/B direct logs")
        return 3

    a_rows: list[dict[str, Any]] = []
    b_rows: list[dict[str, Any]] = []
    for sid in states:
        key = f"STATE_{sid:02d}"
        a_conf = a_by_state[sid]
        b_conf = b_by_state[sid]
        a_snr = _clamp(0.85 + (a_conf - 0.5) * 0.7, 0.6, 1.5)
        b_snr = _clamp(0.85 + (b_conf - 0.5) * 0.7, 0.6, 1.5)
        common = {
            "id": key,
            "state_id": sid,
            "direction": _direction(sid),
            "source": "build_btrack_bench_from_direct_logs",
            "direct_logs": True,
        }
        a_rows.append({**common, "track": "A", "confidence": round(a_conf, 6), "snr": round(a_snr, 6)})
        b_rows.append({**common, "track": "B", "confidence": round(b_conf, 6), "snr": round(b_snr, 6)})

    a_out.parent.mkdir(parents=True, exist_ok=True)
    b_out.parent.mkdir(parents=True, exist_ok=True)
    with a_out.open("w", encoding="utf-8") as fa:
        for row in a_rows:
            fa.write(json.dumps(row, ensure_ascii=False) + "\n")
    with b_out.open("w", encoding="utf-8") as fb:
        for row in b_rows:
            fb.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("OK: direct-log A/B bench generated")
    print(f"a_out={a_out} rows={len(a_rows)}")
    print(f"b_out={b_out} rows={len(b_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
