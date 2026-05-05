#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aggregate metrics from lens_minute_shadow_eval_v1 JSON (shadow / lab stub).

When ``labels_jsonl`` or labeled rows are absent, emits summary stats only and sets label_gate_ready=false.
Does not submit trades. See LENS_MINUTE_SHADOW_EVAL_CONTRACT_V1.json.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "lens_minute_shadow_eval_smoke_latest.json"
DEFAULT_OUT = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "lens_minute_shadow_eval_metrics_latest.json"
SCHEMA_ID = "lens_minute_shadow_eval_metrics_v1"


def _extract_scores(rows: List[Dict[str, Any]]) -> Dict[str, List[float]]:
    mn: List[float] = []
    sa: List[float] = []
    for r in rows:
        snap = r.get("lens_minute_snapshot") or {}
        m = snap.get("myeongni") or {}
        s = snap.get("sasang") or {}
        if isinstance(m.get("direction_score"), (int, float)):
            mn.append(float(m["direction_score"]))
        if isinstance(s.get("intensity_0_1"), (int, float)):
            sa.append(float(s["intensity_0_1"]))
    return {"myeongni_direction": mn, "sasang_intensity": sa}


def build_metrics(doc: Dict[str, Any]) -> Dict[str, Any]:
    if doc.get("schema") != "lens_minute_shadow_eval_v1":
        raise ValueError("input schema must be lens_minute_shadow_eval_v1")
    rows = doc.get("rows") or []
    scores = _extract_scores(rows)
    mn = scores["myeongni_direction"]
    sa = scores["sasang_intensity"]

    out: Dict[str, Any] = {
        "schema": SCHEMA_ID,
        "schema_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "shadow_only": True,
        "source_report_schema": doc.get("schema"),
        "bar_interval_minutes": doc.get("bar_interval_minutes"),
        "n_bars": len(rows),
        "aggregates": {
            "myeongni_direction_mean": statistics.mean(mn) if mn else None,
            "myeongni_direction_stdev": statistics.pstdev(mn) if len(mn) > 1 else None,
            "sasang_intensity_mean": statistics.mean(sa) if sa else None,
            "sasang_intensity_stdev": statistics.pstdev(sa) if len(sa) > 1 else None,
        },
        "label_gate": {
            "label_gate_ready": False,
            "note": "Wire labeled_jsonl or dual-write labels to enable Brier/direction_hit; stub aggregates only.",
        },
        "evolution_stub": {
            "enabled": False,
            "note": "Hook optimizer / bandit here after holdout labels exist (B-track only).",
        },
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Lens minute shadow metrics (aggregate stub).")
    ap.add_argument("--in-json", type=Path, default=DEFAULT_IN, dest="in_json", help="lens_minute_shadow_eval_v1 JSON.")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT, help="Metrics JSON output.")
    args = ap.parse_args()

    doc = json.loads(args.in_json.read_text(encoding="utf-8"))
    metrics = build_metrics(doc)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
