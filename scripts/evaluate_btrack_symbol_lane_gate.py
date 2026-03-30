#!/usr/bin/env python3
"""Evaluate B-Track symbol promotion lanes against gate thresholds."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LANE_SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_lane_summary_latest.json"
GATE_TEMPLATE = ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_lane_gate_template.json"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_lane_gate_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _compute_metrics(path: Path, contamination_terms: set[str]) -> dict[str, float]:
    rows = list(_iter_jsonl(path)) if path.is_file() else []
    if not rows:
        return {
            "count": 0,
            "avg_score_tfidf_like": 0.0,
            "avg_dss_ratio": 0.0,
            "dss_presence_rate": 0.0,
            "contamination_rate": 0.0,
        }

    score_sum = 0.0
    dss_ratio_sum = 0.0
    dss_presence = 0
    contam = 0
    for r in rows:
        score_sum += float(r.get("score_tfidf_like", 0.0) or 0.0)
        mix = r.get("source_mix", {})
        if not isinstance(mix, dict):
            mix = {}
        dss = float(mix.get("dss", 0.0) or 0.0)
        apo = float(mix.get("apocrypha", 0.0) or 0.0)
        total = dss + apo
        ratio = (dss / total) if total > 0 else 0.0
        dss_ratio_sum += ratio
        if dss > 0:
            dss_presence += 1
        sym = str(r.get("symbol", "")).strip().lower()
        if sym in contamination_terms:
            contam += 1

    n = len(rows)
    return {
        "count": float(n),
        "avg_score_tfidf_like": round(score_sum / n, 6),
        "avg_dss_ratio": round(dss_ratio_sum / n, 6),
        "dss_presence_rate": round(dss_presence / n, 6),
        "contamination_rate": round(contam / n, 6),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate B-Track symbol lane gate")
    ap.add_argument("--lane-summary", default=str(LANE_SUMMARY))
    ap.add_argument("--gate", default=str(GATE_TEMPLATE))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    lane_summary_path = _abs(args.lane_summary)
    gate_path = _abs(args.gate)
    out_path = _abs(args.out)
    for p in (lane_summary_path, gate_path):
        if not p.is_file():
            print(f"ERROR: missing file: {p}")
            return 2

    lane_summary = _jread(lane_summary_path)
    gate = _jread(gate_path)
    thresholds = gate.get("thresholds_by_lane", {})
    contamination_terms = {str(x).strip().lower() for x in gate.get("contamination_terms", [])}

    lanes = lane_summary.get("lanes", {})
    results: dict[str, Any] = {}
    overall_pass = True

    for lane_name, lane_payload in lanes.items():
        if not isinstance(lane_payload, dict):
            continue
        lane_path = Path(str(lane_payload.get("path", "")))
        metric = _compute_metrics(lane_path, contamination_terms)
        t = thresholds.get(lane_name, {})
        checks = {
            "count_ok": metric["count"] >= float(t.get("min_count", 0)),
            "avg_score_ok": metric["avg_score_tfidf_like"] >= float(t.get("min_avg_score", 0.0)),
            "dss_presence_ok": metric["dss_presence_rate"] >= float(t.get("min_dss_presence_rate", 0.0)),
            "avg_dss_ratio_ok": metric["avg_dss_ratio"] >= float(t.get("min_avg_dss_ratio", 0.0)),
            "contamination_ok": metric["contamination_rate"] <= float(t.get("max_contamination_rate", 1.0)),
        }
        lane_decision = "pass" if all(checks.values()) else "hold"
        if lane_decision != "pass":
            overall_pass = False
        results[lane_name] = {
            "input_path": str(lane_path),
            "metrics": metric,
            "thresholds": t,
            "checks": checks,
            "decision": lane_decision,
        }

    out = {
        "schema": "btrack_symbol_lane_gate_result_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "lane_summary": str(lane_summary_path),
            "gate_template": str(gate_path),
        },
        "lanes": results,
        "decision": "pass" if overall_pass else "hold",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: symbol lane gate decision={out['decision']}")
    print(f"out={out_path}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
