#!/usr/bin/env python3
"""COMP-ATOM-05: per-case graph_wire bridge_boost detail for V2 40-case bench."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_atom05_bridge_boost_detail_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    from scripts.mkm_graph_wire_bridge_influence_v1 import (  # noqa: WPS433
        DEFAULT_BRIDGE_BOOST_MIN_SCORE,
        build_influence_map_from_compression_cases,
        wire_atom_ids_from_poc,
    )

    if not INPUT_V2.is_file():
        print(f"missing {INPUT_V2}", file=sys.stderr)
        return 1

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    cases = list(src.get("compression_cases") or [])
    influence = build_influence_map_from_compression_cases(
        cases, wire_atom_ids=wire_atom_ids_from_poc()
    )

    rows = []
    for cid in sorted(influence.keys()):
        inf = influence[cid]
        rows.append(
            {
                "case_id": cid,
                "bridge_boost": bool(inf.get("bridge_boost")),
                "wire_influence_score": inf.get("wire_influence_score"),
                "expanded_node_count": inf.get("expanded_node_count"),
                "graph_anchor_terms": inf.get("graph_anchor_terms"),
                "atom_id_sequence_len": len(inf.get("atom_id_sequence") or []),
            }
        )

    boosted = [r for r in rows if r["bridge_boost"]]
    not_boosted = [r for r in rows if not r["bridge_boost"]]

    report = {
        "schema": "comp_atom05_bridge_boost_detail_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "b_track_comp_atom05",
        "bench": "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        "bridge_boost_min_score": DEFAULT_BRIDGE_BOOST_MIN_SCORE,
        "summary": {
            "cases_total": len(rows),
            "bridge_boost_count": len(boosted),
            "not_boosted_count": len(not_boosted),
        },
        "bridge_boost_cases": boosted,
        "not_boosted_cases": not_boosted,
        "aggregate_wire_selective_delta": {
            "note": "See comp_atom05_profile_matrix_brief_v1.json full_v2_40 economy_plus_wire",
            "saving_pp_approx": -0.0042,
            "jaccard_pp_approx": 0.0063,
        },
        "headline": (
            f"{len(boosted)}/{len(rows)} cases receive bridge_boost under graph_wire_selective; "
            "semantic channel only — Track A remains economy 47.5% bridge OFF."
        ),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"wrote": OUT.name, "boost": len(boosted), "total": len(rows)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
