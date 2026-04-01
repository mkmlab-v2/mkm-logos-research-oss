#!/usr/bin/env python3
"""Build A/B bench from direct in-workspace logs (no synthetic uplift model).

Default outputs are *suffixed* (…/a_track_eval_direct_v1.jsonl) so they do not
overwrite the canonical bench; see data/logos/btrack_pilot/bench/CANONICAL_BENCH_POINTER_V1.json.

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
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.myeongni.btrack_bench_paths import (
    DIRECT_A_TRACK_EVAL,
    DIRECT_B_TRACK_EVAL,
)
from tools.myeongni.manseryeok_provenance import (
    BENCH_SCOPE_MANIFEST_RELPATH,
    BENCH_SCOPE_REF_DIRECT_V1,
    btrack_pilot_bench_scope,
    upsert_bench_manseryeok_scope_manifest,
)
AUDIT_LOG = ROOT / "data" / "myeongni" / "myeongni_16_state_audit_v1.jsonl"
BTRACK_LOG = ROOT / "data" / "myeongni" / "myeongni_16_state_experiment_20260329.jsonl"
A_OUT = ROOT / DIRECT_A_TRACK_EVAL
B_OUT = ROOT / DIRECT_B_TRACK_EVAL


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

    scope = btrack_pilot_bench_scope(
        build_script="build_btrack_bench_from_direct_logs.py",
        source_note=(
            "Sources: myeongni_16_state_audit_v1.jsonl + myeongni_16_state_experiment_*.jsonl "
            "(vector_4d / consistency); no birth datetime pipeline."
        ),
    )
    upsert_bench_manseryeok_scope_manifest(ROOT, BENCH_SCOPE_REF_DIRECT_V1, scope)

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
            "manseryeok_scope_ref": BENCH_SCOPE_REF_DIRECT_V1,
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
    print(f"manseryeok_manifest={ROOT / BENCH_SCOPE_MANIFEST_RELPATH}")
    print(f"a_out={a_out} rows={len(a_rows)}")
    print(f"b_out={b_out} rows={len(b_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
