#!/usr/bin/env python3
"""Logos Bible advancement completion chain — HD delegation M closeout (HYPO).

Reproducible:
  py scripts/run_logos_bible_advancement_completion_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOSURE = ROOT / "docs/final/artifacts/logos_bible_advancement_closure_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    chain_steps = [
        "scripts/run_logos_physics_alignment_chain_v1.py --skip-pytest",
        "scripts/run_logos_adv3_graphrag_bridge_chain_v1.py",
        "scripts/run_logos_narrative_path_eval_chain_v1.py --skip-pytest",
        "scripts/build_logos_fundamental_force_primitive_report_v1.py",
    ]
    for script in chain_steps:
        parts = script.split()
        proc = subprocess.run([sys.executable, *parts], cwd=ROOT, check=False)
        if proc.returncode != 0:
            print(f"FAIL: {script} exit {proc.returncode}", file=sys.stderr)
            return proc.returncode
        print(f"OK: {parts[0]}")

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_logos_cosmic_anchor_graph_bridge_v1.py",
                "tests/test_logos_fundamental_force_lexicon_v1.py",
                "tests/test_logos_corpus_expansion_wave_v1.py",
                "tests/test_logos_cosmic_anchor_batch_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest")

    bridge = json.loads(
        (ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    dual = json.loads(
        (ROOT / "docs/final/artifacts/logos_anchor_resonance_dual_gate_latest.json").read_text(
            encoding="utf-8"
        )
    )
    closure = {
        "schema": "logos_bible_advancement_closure_v1",
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "anchor_count": bridge.get("anchor_count"),
        "lemma_hit_anchors": bridge["summary"]["lemma_hit_anchors"],
        "meaning_graph_hit_anchors": bridge["summary"]["meaning_graph_hit_anchors"],
        "narrative_sample_count": bridge["summary"]["narrative_sample_count"],
        "dual_gate_all_research": dual.get("wave25_pass", {}).get("all_research_gates"),
        "harmony_top1_share": dual.get("gates", {})
        .get("gate_a_ranking_production", {})
        .get("harmony_top1_share"),
        "reproducible_command": "py scripts/run_logos_bible_advancement_completion_chain_v1.py",
    }
    eval_path = ROOT / "docs/final/artifacts/logos_narrative_path_eval_v1_latest.json"
    if eval_path.is_file():
        ev = json.loads(eval_path.read_text(encoding="utf-8"))
        closure["narrative_path_eval"] = {
            "path_ok_rate": ev.get("summary", {}).get("path_ok_rate"),
            "flow_pass_rate": ev.get("summary", {}).get("flow_pass_rate"),
            "sample_pass_rate": ev.get("summary", {}).get("sample_pass_rate"),
            "router_hit_rate": ev.get("summary", {}).get("router_hit_rate"),
        }
    lemma_overlap_path = ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json"
    if lemma_overlap_path.is_file():
        lo = json.loads(lemma_overlap_path.read_text(encoding="utf-8"))
        closure["narrative_lemma_overlap_eval"] = {
            "hop_lemma_edge_hit_rate": lo.get("summary", {}).get("hop_lemma_edge_hit_rate"),
            "hop_bidirectional_atom_hit_rate": lo.get("summary", {}).get(
                "hop_bidirectional_atom_hit_rate"
            ),
            "mean_inter_hop_atom_jaccard": lo.get("summary", {}).get("mean_inter_hop_atom_jaccard"),
            "mean_inter_hop_lemma_jaccard": lo.get("summary", {}).get("mean_inter_hop_lemma_jaccard"),
            "mean_inter_hop_bridge_lemma_jaccard": lo.get("summary", {}).get(
                "mean_inter_hop_bridge_lemma_jaccard"
            ),
            "curated_bridge_pair_rate": lo.get("summary", {}).get("curated_bridge_pair_rate"),
        }
    CLOSURE.parent.mkdir(parents=True, exist_ok=True)
    CLOSURE.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {CLOSURE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
