#!/usr/bin/env python3
"""Compare baseline vs bridge_v2 overlay dedupe + organic topic spike (B-track)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_DEDUPE = ROOT / "reports/logos_verse_4d_dedupe_audit_v1_latest.json"
BASELINE_SPIKE = ROOT / "reports/logos_topic_4d_resonance_spike_v1_latest.json"
SKETCH = ROOT / "reports/logos_4d_bridge_redesign_sketch_v1_latest.json"
OUT = ROOT / "reports/logos_4d_bridge_v2_poc_compare_v1_latest.json"


def _read(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _organic_hits(spike: dict) -> tuple[int, int]:
    topics = spike.get("topics") or []
    hits = sum(1 for t in topics if (t.get("seed_in_top_k") or []))
    return hits, len(topics)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-dedupe", type=Path, default=BASELINE_DEDUPE)
    ap.add_argument("--v2-dedupe", type=Path, required=True)
    ap.add_argument("--baseline-spike", type=Path, default=BASELINE_SPIKE)
    ap.add_argument("--v2-spike", type=Path, required=True)
    ap.add_argument("--sketch-json", type=Path, default=SKETCH)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    b_ded = _read(args.baseline_dedupe)
    v2_ded = _read(args.v2_dedupe)
    b_sp = _read(args.baseline_spike)
    v2_sp = _read(args.v2_spike)
    sketch = _read(args.sketch_json)
    gates = (sketch.get("eval_gates_proposed") or {}) if sketch else {}

    b_hits, b_n = _organic_hits(b_sp)
    v2_hits, v2_n = _organic_hits(v2_sp)

    b_tot = (b_ded.get("totals") or {}) if b_ded else {}
    v2_tot = (v2_ded.get("totals") or {}) if v2_ded else {}

    unique_v2 = int(v2_tot.get("unique_vector_keys") or 0)
    if "duplicate_verse_fraction" in v2_tot:
        dup_frac_v2 = float(v2_tot["duplicate_verse_fraction"])
    else:
        dup_frac_v2 = 1.0

    gate_eval = {
        "unique_vector_keys_min": int(gates.get("unique_vector_keys_min") or 0),
        "duplicate_row_fraction_max": float(gates.get("duplicate_row_fraction_max") or 1.0),
        "organic_topic_spike_min": int(gates.get("organic_topic_spike_min") or 0),
        "v2_unique_keys_pass": unique_v2 >= int(gates.get("unique_vector_keys_min") or 0),
        "v2_dup_fraction_pass": dup_frac_v2 <= float(gates.get("duplicate_row_fraction_max") or 1.0),
        "v2_organic_spike_pass": v2_hits >= int(gates.get("organic_topic_spike_min") or 0),
    }
    discrimination_pass = gate_eval["v2_unique_keys_pass"] and gate_eval["v2_dup_fraction_pass"]
    retrieval_pass = gate_eval["v2_organic_spike_pass"]
    research_pass = discrimination_pass and retrieval_pass

    doc = {
        "schema": "logos_4d_bridge_v2_poc_compare_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "final_action": "HOLD_EXPLORATION" if not research_pass else "WATCH_POC",
        "baseline": {
            "dedupe": {
                "unique_vector_keys": b_tot.get("unique_vector_keys"),
                "duplicate_verse_fraction": b_tot.get("duplicate_verse_fraction"),
            },
            "organic_spike": f"{b_hits}/{b_n}",
        },
        "bridge_v2_overlay": {
            "dedupe": {
                "unique_vector_keys": v2_tot.get("unique_vector_keys"),
                "duplicate_verse_fraction": v2_tot.get("duplicate_verse_fraction"),
                "max_cluster_size": v2_tot.get("max_cluster_size"),
            },
            "organic_spike": f"{v2_hits}/{v2_n}",
        },
        "delta": {
            "unique_vector_keys": (v2_tot.get("unique_vector_keys") or 0) - (b_tot.get("unique_vector_keys") or 0),
            "duplicate_verse_fraction": round(
                float(v2_tot.get("duplicate_verse_fraction") or 0) - float(b_tot.get("duplicate_verse_fraction") or 0),
                6,
            ),
            "organic_spike_hits": v2_hits - b_hits,
        },
        "proposed_gate_eval": gate_eval,
        "discrimination_pass": discrimination_pass,
        "retrieval_pass": retrieval_pass,
        "research_poc_pass": research_pass,
        "interpretation_guard": "PoC pass is B-track research only — not Track A / gold router / live promotion.",
        "pointers": {
            "overlay_jsonl": "reports/logos_verse_4d_bridge_v2_overlay_v1_latest.jsonl",
            "sketch": str(args.sketch_json.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "research_poc_pass": research_pass,
                "v2_organic": f"{v2_hits}/{v2_n}",
                "v2_unique_keys": unique_v2,
                "out": str(args.out_json),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
