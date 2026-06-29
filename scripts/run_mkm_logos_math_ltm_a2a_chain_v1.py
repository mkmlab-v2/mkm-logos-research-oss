#!/usr/bin/env python3
"""Phase 2 Logos LTM graph + A2A trust packet chain ([HYPO] / B-track).

  py scripts/run_mkm_logos_math_ltm_a2a_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "storage/meta/mkm_long_term_memory_graph_v1.json"
INDEX = ROOT / "storage/meta/mkm_ops_memory_index_v1.json"
BRIDGE_MAP = ROOT / "reports/ltm_a2a_bridge_map_v1_latest.json"
TRUST_PKT = ROOT / "docs/final/artifacts/logos_a2a_trust_packet_v1_latest.json"
DIALOGUE = ROOT / "docs/final/artifacts/mkm_inter_agent_dialogue_mock_summary_latest.json"
OUT = ROOT / "reports/mkm_logos_math_ltm_a2a_chain_v1_latest.json"

LOGOS_CONCEPT_IDS = (
    "logos_cosmic_anchor_graph_math",
    "logos_router_regression_bundle",
    "logos_4d_state_non_gating",
    "logos_gematria_dual_gate",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    steps: list[dict] = []
    scripts = [
        ("build_mkm_long_term_memory_graph_v1.py", ["--skip-post-gate"]),
        (
            "build_mkm_ops_memory_doctrine_overlay_v1.py",
            ["--topic", "logos gematria router 4d cosmic anchor", "--max-nodes", "8"],
        ),
        "build_mkm_ops_memory_logos_math_overlay_v1.py",
        "build_ltm_a2a_bridge_map_v1.py",
        "build_logos_a2a_trust_packet_v1.py",
        (
            "run_mkm_inter_agent_dialogue_mock_v1.py",
            ["--scenario", "logos_math", "--turns", "4"],
        ),
    ]
    for item in scripts:
        if isinstance(item, tuple):
            script, extra = item
            cmd = [sys.executable, f"scripts/{script}", *extra]
        else:
            script = item
            cmd = [sys.executable, f"scripts/{script}"]
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        steps.append({"step": script, "exit_code": proc.returncode})
        if proc.returncode != 0:
            return proc.returncode
        print(f"OK: {script}")

    graph = json.loads(GRAPH.read_text(encoding="utf-8-sig"))
    concepts = graph.get("concepts") or {}
    missing = [cid for cid in LOGOS_CONCEPT_IDS if cid not in concepts]
    if missing:
        print(f"FAIL: LTM concepts missing {missing}", file=sys.stderr)
        return 1

    index = json.loads(INDEX.read_text(encoding="utf-8-sig"))
    ltm_nodes = [k for k in (index.get("nodes") or {}) if k.startswith("ltm_logos_")]
    if len(ltm_nodes) < 2:
        print(f"FAIL: ltm_logos_* doctrine overlay nodes={len(ltm_nodes)}", file=sys.stderr)
        return 1

    bridge = json.loads(BRIDGE_MAP.read_text(encoding="utf-8-sig"))
    if int(bridge.get("ltm_overlay_count") or 0) < 1:
        print("FAIL: ltm_a2a bridge map empty", file=sys.stderr)
        return 1

    trust = json.loads(TRUST_PKT.read_text(encoding="utf-8-sig"))
    refs = trust.get("logos_wire_refs") or {}
    if not refs.get("vector_4d") or not refs.get("anchor_ids"):
        print("FAIL: logos_a2a trust packet missing wire refs", file=sys.stderr)
        return 1
    if trust.get("compress_result", {}).get("decision") != "compressed":
        print("FAIL: logos_a2a trust packet not compressed", file=sys.stderr)
        return 1

    dialogue = json.loads(DIALOGUE.read_text(encoding="utf-8-sig"))
    if dialogue.get("scenario") != "logos_math":
        print("FAIL: dialogue mock scenario not logos_math", file=sys.stderr)
        return 1
    if not dialogue.get("all_compress_ok"):
        print("FAIL: dialogue mock compress failed", file=sys.stderr)
        return 1

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_mkm_logos_math_ltm_a2a_chain_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest logos math ltm a2a chain")

    report = {
        "schema": "mkm_logos_math_ltm_a2a_chain_v1",
        "chain_pass": True,
        "research_only": True,
        "send_gate": refs.get("send_gate", "HOLD"),
        "logos_concept_ids": list(LOGOS_CONCEPT_IDS),
        "ltm_logos_overlay_nodes": sorted(ltm_nodes),
        "logos_wire_refs": {
            "anchor_id_count": len(refs.get("anchor_ids") or []),
            "vector_4d": refs.get("vector_4d"),
            "router_hit_rate": refs.get("router_hit_rate"),
            "bloom_cap": refs.get("bloom_cap"),
        },
        "dialogue_scenario": dialogue.get("scenario"),
        "dialogue_turns": dialogue.get("turns_recorded"),
        "steps": steps,
        "repro_one_shot": "py scripts/run_mkm_logos_math_ltm_a2a_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"chain_pass=true ltm_logos_nodes={len(ltm_nodes)} "
        f"anchors={len(refs.get('anchor_ids') or [])} scenario=logos_math"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
