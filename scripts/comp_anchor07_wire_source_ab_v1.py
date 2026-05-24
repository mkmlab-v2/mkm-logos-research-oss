#!/usr/bin/env python3
"""B-track: logos 10 subset — wire_atom_ids source poc vs anchor07 vs merged."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.comp_graphrag_philosophy_compression_sweep_v1 import (  # noqa: E402
    BASE_MUST_KEEP,
    INPUT_V2,
    _base_eval_kwargs,
    _metrics,
    _utc,
)
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

SUBSET = ROOT / "docs/final/artifacts/MULTILENS_LOGOS_GRAPH_SUBSET_V1.json"
PILOT = ROOT / "reports/constitution/btrack_pilot"
OUT = PILOT / "comp_anchor07_wire_source_ab_v1.json"


def _subset_src() -> dict[str, Any]:
    if SUBSET.is_file():
        doc = json.loads(SUBSET.read_text(encoding="utf-8"))
        if doc.get("compression_cases"):
            return {"compression_cases": list(doc["compression_cases"])}
        ids = {str(x) for x in (doc.get("case_ids") or [])}
        if ids:
            full = json.loads(INPUT_V2.read_text(encoding="utf-8"))
            cases = [
                c for c in (full.get("compression_cases") or []) if str(c.get("id", "")) in ids
            ]
            return {"compression_cases": cases}
    full = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    return {"compression_cases": list(full.get("compression_cases") or [])}


def _eval_wire(src: dict[str, Any], source: str, atoms: list[str]) -> dict[str, Any]:
    from scripts.mkm_graph_wire_bridge_influence_v1 import (  # noqa: E402
        build_influence_map_from_compression_cases,
    )

    cases = list(src.get("compression_cases") or [])
    influence = build_influence_map_from_compression_cases(cases, wire_atom_ids=atoms)
    kw = _base_eval_kwargs()
    kw["apply_gematria_4d_bridge_policy"] = False
    report = evaluate_report(
        src,
        must_keep=set(BASE_MUST_KEEP),
        graph_wire_selective_bridge=True,
        case_graph_wire_influence=influence,
        emit_semantic_pointer=True,
        **kw,
    )
    return {
        "wire_atom_source": source,
        "wire_atom_count": len(atoms),
        "bridge_boost_cases": sum(1 for v in influence.values() if v.get("bridge_boost")),
        "metrics": _metrics(report),
    }


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    src = _subset_src()
    from scripts.mkm_graph_wire_bridge_influence_v1 import (  # noqa: E402
        wire_atom_ids_from_anchor07,
        wire_atom_ids_from_poc,
        wire_atom_ids_merged,
    )

    combos = [
        _eval_wire(src, "poc", wire_atom_ids_from_poc()),
        _eval_wire(src, "anchor07", wire_atom_ids_from_anchor07()),
        _eval_wire(src, "merged", wire_atom_ids_merged()),
    ]
    doc = {
        "schema": "comp_anchor07_wire_source_ab_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "bench": "logos_graph_subset_10",
        "subset_artifact": "docs/final/artifacts/MULTILENS_LOGOS_GRAPH_SUBSET_V1.json",
        "combos": combos,
        "note": "Same graph routes; only base wire_atom_ids list differs. Track A untouched.",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "combos": combos}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
