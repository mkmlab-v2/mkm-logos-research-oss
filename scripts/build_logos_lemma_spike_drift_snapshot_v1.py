#!/usr/bin/env python3
"""Oracle lemma-spike drift baseline — pre/post Lemma-60 metrics (HYPO)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
DUAL = ROOT / "docs/final/artifacts/logos_anchor_resonance_dual_gate_latest.json"
OVERLAP = ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json"
NARRATIVE_EVAL = ROOT / "docs/final/artifacts/logos_narrative_path_eval_v1_latest.json"
BASELINE = ROOT / "docs/final/artifacts/logos_lemma_spike_drift_baseline_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/logos_lemma_spike_drift_check_v1_latest.json"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics() -> dict[str, Any]:
    bridge = _load(BRIDGE)
    dual = _load(DUAL)
    overlap = _load(OVERLAP)
    narrative = _load(NARRATIVE_EVAL)
    return {
        "lemma_hit_anchors": (bridge.get("summary") or {}).get("lemma_hit_anchors"),
        "meaning_graph_hit_anchors": (bridge.get("summary") or {}).get("meaning_graph_hit_anchors"),
        "narrative_sample_count": (bridge.get("summary") or {}).get("narrative_sample_count"),
        "dual_gate_all_research": ((dual.get("wave25_pass") or {}).get("all_research_gates")),
        "harmony_top1_share": ((dual.get("gates") or {}).get("gate_a_ranking_production") or {}).get(
            "harmony_top1_share"
        ),
        "hop_lemma_edge_hit_rate": ((overlap.get("summary") or {}).get("hop_lemma_edge_hit_rate")),
        "curated_bridge_pair_rate": ((overlap.get("summary") or {}).get("curated_bridge_pair_rate")),
        "narrative_sample_pass_rate": ((narrative.get("summary") or {}).get("sample_pass_rate")),
    }


def _drift_flags(baseline: dict[str, Any], current: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if baseline.get("dual_gate_all_research") is True and current.get("dual_gate_all_research") is not True:
        flags.append("dual_gate_research_broken")
    if (current.get("narrative_sample_pass_rate") or 0) < 1.0:
        flags.append("narrative_eval_regressed")
    if (current.get("hop_lemma_edge_hit_rate") or 0) < 1.0:
        flags.append("narrative_hop_lemma_regressed")
    if (current.get("curated_bridge_pair_rate") or 0) < 1.0:
        flags.append("inter_hop_bridge_regressed")
    b_lemma = baseline.get("lemma_hit_anchors")
    c_lemma = current.get("lemma_hit_anchors")
    if b_lemma is not None and c_lemma is not None and int(c_lemma) < int(b_lemma):
        flags.append("lemma_hit_anchors_regressed")
    harm = current.get("harmony_top1_share")
    if harm is not None and float(harm) > 0.65:
        flags.append("harmony_top1_share_above_guard")
    return flags


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    current = _metrics()

    if args.write_baseline:
        doc = {
            "schema": "logos_lemma_spike_drift_baseline_v1",
            "generated_at_utc": now,
            "hypothesis_class": "HYPO",
            "research_only": True,
            "metrics": current,
            "reproducible_command": "py scripts/build_logos_lemma_spike_drift_snapshot_v1.py --write-baseline",
        }
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {BASELINE}")
        return 0

    baseline_doc = _load(BASELINE)
    baseline = baseline_doc.get("metrics") or {}
    flags = _drift_flags(baseline, current) if baseline else []
    check = {
        "schema": "logos_lemma_spike_drift_check_v1",
        "generated_at_utc": now,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "baseline_generated_at_utc": baseline_doc.get("generated_at_utc"),
        "baseline_metrics": baseline,
        "current_metrics": current,
        "drift_flags": flags,
        "pass": len(flags) == 0,
        "observation_window_ko": "72h compressed — D1 baseline vs D2+ check",
        "reproducible_command": "py scripts/build_logos_lemma_spike_drift_snapshot_v1.py --compare",
    }
    OUT.write_text(json.dumps(check, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(f"  drift_flags={flags} pass={check['pass']}")
    return 0 if check["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
