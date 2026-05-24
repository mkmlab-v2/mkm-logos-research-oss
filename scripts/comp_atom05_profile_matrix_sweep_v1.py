#!/usr/bin/env python3
"""COMP-ATOM-05: 4-cell profile matrix (economy/fidelity × wire on/off) — B-track."""

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
    GATE,
    INPUT_V2,
    _base_eval_kwargs,
    _metrics,
    _utc,
)
from scripts.compression_profile_v1 import profile_evaluate_report_kwargs  # noqa: E402
from scripts.mkm_graph_wire_bridge_influence_v1 import (  # noqa: E402
    build_influence_map_from_compression_cases,
    wire_atom_ids_from_poc,
)
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

SUBSET = ROOT / "docs/final/artifacts/MULTILENS_LOGOS_GRAPH_SUBSET_V1.json"
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT = PILOT / "comp_atom05_profile_matrix_sweep_v1.json"


def _eval_cell(
    src: dict[str, Any],
    cell_id: str,
    *,
    profile: str | None,
    wire: bool,
    influence: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    kw = _base_eval_kwargs()
    bridge_global = False
    if profile == "fidelity":
        prof = profile_evaluate_report_kwargs("fidelity")
        kw.update(prof)
        bridge_global = bool(prof.get("apply_gematria_4d_bridge_policy"))
    elif profile == "economy":
        if wire:
            # Match comp_atom05_full_v2 wire_selective: bench kwargs + per-case bridge only.
            kw["apply_gematria_4d_bridge_policy"] = False
            bridge_global = False
        else:
            prof = profile_evaluate_report_kwargs("economy")
            kw.update(prof)
            bridge_global = bool(prof.get("apply_gematria_4d_bridge_policy"))

    report = evaluate_report(
        src,
        must_keep=set(BASE_MUST_KEEP),
        graph_wire_selective_bridge=wire,
        case_graph_wire_influence=influence if wire else None,
        emit_semantic_pointer=True,
        **kw,
    )
    return {
        "cell_id": cell_id,
        "compression_profile": profile or "bench_default",
        "graph_wire_selective_bridge": wire,
        "apply_gematria_4d_bridge_policy_global": bridge_global,
        "metrics": _metrics(report),
    }


def _matrix_for_input(
    src: dict[str, Any],
    *,
    bench_label: str,
) -> dict[str, Any]:
    cases = list(src.get("compression_cases") or [])
    influence = build_influence_map_from_compression_cases(
        cases, wire_atom_ids=wire_atom_ids_from_poc()
    )
    cells = [
        _eval_cell(src, "economy", profile="economy", wire=False, influence=influence),
        _eval_cell(src, "economy_plus_wire", profile="economy", wire=True, influence=influence),
        _eval_cell(src, "fidelity", profile="fidelity", wire=False, influence=influence),
        _eval_cell(src, "fidelity_plus_wire", profile="fidelity", wire=True, influence=influence),
    ]
    return {
        "bench_label": bench_label,
        "compression_cases": len(cases),
        "bridge_boost_cases": sum(1 for v in influence.values() if v.get("bridge_boost")),
        "cells": cells,
    }


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    status = str(((gate.get("summary") or {}).get("status")) or "").upper()
    if status != "GO":
        print(json.dumps({"error": f"gate not GO: {status}"}, ensure_ascii=False))
        return 3

    if not SUBSET.is_file():
        print(json.dumps({"error": "run build_multilens_logos_graph_subset_v1.py first"}, ensure_ascii=False))
        return 2

    full = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    subset = json.loads(SUBSET.read_text(encoding="utf-8"))

    doc = {
        "schema": "comp_atom05_profile_matrix_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "b_track_comp_atom05",
        "active_report_untouched": True,
        "gate_status": status,
        "matrices": [
            _matrix_for_input(full, bench_label="full_v2_40"),
            _matrix_for_input(subset, bench_label="logos_graph_subset_10"),
        ],
        "compare_prior": "reports/constitution/btrack_pilot/comp_atom05_compare_prior_v1.json",
        "note": (
            "fidelity+wire on full bench may match fidelity alone when global bridge already ON; "
            "subset shows wire lift on economy tier."
        ),
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    full_cells = doc["matrices"][0]["cells"]
    print(
        json.dumps(
            {
                "wrote": str(OUT.relative_to(ROOT)),
                "full_v2": {c["cell_id"]: c["metrics"] for c in full_cells},
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
