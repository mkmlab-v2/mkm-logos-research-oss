#!/usr/bin/env python3
"""Compare stable vs exploratory symbol lane outputs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"

DEFAULT_STABLE_GATE = PILOT / "symbol_lane_gate_stable_latest.json"
DEFAULT_EXPL_GATE = PILOT / "symbol_lane_gate_exploratory_latest.json"
DEFAULT_STABLE_THEMATIC = PILOT / "symbol_top50_by_source_thematic_stable_latest.json"
DEFAULT_EXPL_THEMATIC = PILOT / "symbol_top50_by_source_thematic_exploratory_latest.json"
DEFAULT_STABLE_C_QUEUE = PILOT / "symbol_c_validation_queue_stable_latest.jsonl"
DEFAULT_EXPL_C_QUEUE = PILOT / "symbol_c_validation_queue_exploratory_latest.jsonl"
DEFAULT_OUT = PILOT / "symbol_lane_profile_compare_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _lane_metric(gate: dict[str, Any], lane: str, metric: str) -> float:
    payload = gate.get("lanes", {}).get(lane, {})
    value = payload.get("metrics", {}).get(metric, 0.0)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _thematic_count(doc: dict[str, Any], key: str) -> int:
    v = doc.get("counts", {}).get(key, 0)
    if isinstance(v, (int, float)):
        return int(v)
    return 0


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _c_queue_stats(path: Path, overlap_k: int = 20) -> dict[str, Any]:
    rows = list(_iter_jsonl(path))
    count = len(rows)
    if count == 0:
        return {"count": 0, "avg_score": 0.0, "top_symbols": [], "top_k_used": overlap_k}
    scores = [float(r.get("score_tfidf_like", 0.0) or 0.0) for r in rows]
    top_symbols = [str(r.get("symbol", "")).strip() for r in rows[:overlap_k]]
    return {
        "count": count,
        "avg_score": round(sum(scores) / count, 6),
        "top_symbols": top_symbols,
        "top_k_used": overlap_k,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare stable vs exploratory lane outputs")
    ap.add_argument("--stable-gate", default=str(DEFAULT_STABLE_GATE))
    ap.add_argument("--exploratory-gate", default=str(DEFAULT_EXPL_GATE))
    ap.add_argument("--stable-thematic", default=str(DEFAULT_STABLE_THEMATIC))
    ap.add_argument("--exploratory-thematic", default=str(DEFAULT_EXPL_THEMATIC))
    ap.add_argument("--stable-c-queue", default=str(DEFAULT_STABLE_C_QUEUE))
    ap.add_argument("--exploratory-c-queue", default=str(DEFAULT_EXPL_C_QUEUE))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    stable_gate_path = _abs(args.stable_gate)
    expl_gate_path = _abs(args.exploratory_gate)
    stable_thematic_path = _abs(args.stable_thematic)
    expl_thematic_path = _abs(args.exploratory_thematic)
    stable_c_queue_path = _abs(args.stable_c_queue)
    expl_c_queue_path = _abs(args.exploratory_c_queue)
    out_path = _abs(args.out_json)

    exploratory_mirror = False
    for p in (stable_gate_path, stable_thematic_path, stable_c_queue_path):
        if not p.is_file():
            print(f"ERROR: missing stable file: {p}")
            return 2
    if not all(
        p.is_file()
        for p in (expl_gate_path, expl_thematic_path, expl_c_queue_path)
    ):
        exploratory_mirror = True
        expl_gate_path = stable_gate_path
        expl_thematic_path = stable_thematic_path
        expl_c_queue_path = stable_c_queue_path
        print(
            "[warn] exploratory lane artifacts missing; using stable paths as mirror (delta will be 0)."
        )

    stable_gate = _jread(stable_gate_path)
    expl_gate = _jread(expl_gate_path)
    stable_thematic = _jread(stable_thematic_path)
    expl_thematic = _jread(expl_thematic_path)

    stable_dss_count = _lane_metric(stable_gate, "dss_priority", "count")
    expl_dss_count = _lane_metric(expl_gate, "dss_priority", "count")
    stable_dss_ratio = _lane_metric(stable_gate, "dss_priority", "avg_dss_ratio")
    expl_dss_ratio = _lane_metric(expl_gate, "dss_priority", "avg_dss_ratio")

    stable_raw = _thematic_count(stable_thematic, "raw")
    expl_raw = _thematic_count(expl_thematic, "raw")
    stable_filtered = _thematic_count(stable_thematic, "filtered_in")
    expl_filtered = _thematic_count(expl_thematic, "filtered_in")
    stable_c = _c_queue_stats(stable_c_queue_path)
    expl_c = _c_queue_stats(expl_c_queue_path)
    stable_top = set(stable_c["top_symbols"])
    expl_top = set(expl_c["top_symbols"])
    overlap = len(stable_top & expl_top)
    overlap_rate = round((overlap / max(1, min(len(stable_top), len(expl_top)))), 6)

    report = {
        "schema": "btrack_symbol_lane_profile_compare_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "stable_gate": str(stable_gate_path),
            "exploratory_gate": str(expl_gate_path),
            "stable_thematic": str(stable_thematic_path),
            "exploratory_thematic": str(expl_thematic_path),
            "stable_c_queue": str(stable_c_queue_path),
            "exploratory_c_queue": str(expl_c_queue_path),
            "exploratory_profile_used_stable_mirror": exploratory_mirror,
        },
        "decisions": {
            "stable": stable_gate.get("decision"),
            "exploratory": expl_gate.get("decision"),
        },
        "dss_priority_delta": {
            "stable_count": stable_dss_count,
            "exploratory_count": expl_dss_count,
            "delta_count": round(expl_dss_count - stable_dss_count, 6),
            "stable_avg_dss_ratio": stable_dss_ratio,
            "exploratory_avg_dss_ratio": expl_dss_ratio,
            "delta_avg_dss_ratio": round(expl_dss_ratio - stable_dss_ratio, 6),
        },
        "thematic_volume_delta": {
            "stable_raw": stable_raw,
            "exploratory_raw": expl_raw,
            "delta_raw": expl_raw - stable_raw,
            "stable_filtered_in": stable_filtered,
            "exploratory_filtered_in": expl_filtered,
            "delta_filtered_in": expl_filtered - stable_filtered,
        },
        "c_queue_delta": {
            "stable_count": stable_c["count"],
            "exploratory_count": expl_c["count"],
            "delta_count": expl_c["count"] - stable_c["count"],
            "stable_avg_score": stable_c["avg_score"],
            "exploratory_avg_score": expl_c["avg_score"],
            "delta_avg_score": round(float(expl_c["avg_score"]) - float(stable_c["avg_score"]), 6),
            "top_overlap_k": stable_c["top_k_used"],
            "top_overlap_count": overlap,
            "top_overlap_rate": overlap_rate,
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: symbol lane profile compare generated")
    print(f"out={out_path}")
    print(f"dss_delta_count={report['dss_priority_delta']['delta_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
