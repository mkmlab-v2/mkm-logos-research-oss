#!/usr/bin/env python3
"""COMP-ATOM-05: full V2 40-case sweep — wire selective bridge vs baseline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.comp_graphrag_philosophy_compression_sweep_v1 import (  # noqa: E402
    BASE_MUST_KEEP,
    GATE,
    INPUT_V2,
    PILOT,
    _base_eval_kwargs,
    _eval_combo,
    _utc,
)
from scripts.mkm_graph_wire_bridge_influence_v1 import (  # noqa: E402
    build_influence_map_from_compression_cases,
    wire_atom_ids_from_poc,
)

OUT = PILOT / "comp_atom05_full_v2_sweep_v1.json"


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    status = str(((gate.get("summary") or {}).get("status")) or "").upper()
    if status != "GO":
        print(json.dumps({"error": f"gate not GO: {status}"}, ensure_ascii=False))
        return 3

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    cases = list(src.get("compression_cases") or [])
    influence = build_influence_map_from_compression_cases(
        cases, wire_atom_ids=wire_atom_ids_from_poc()
    )
    boost_n = sum(1 for v in influence.values() if v.get("bridge_boost"))

    kw = _base_eval_kwargs()

    def _eval_wire_selective() -> dict:
        from scripts.report_multilens_performance_eval import evaluate_report  # noqa: WPS433

        report = evaluate_report(
            src,
            must_keep=set(BASE_MUST_KEEP),
            apply_gematria_4d_bridge_policy=False,
            graph_wire_selective_bridge=True,
            case_graph_wire_influence=influence,
            emit_semantic_pointer=True,
            **kw,
        )
        from scripts.comp_graphrag_philosophy_compression_sweep_v1 import _metrics  # noqa: WPS433

        sp_n = sum(
            1
            for r in (report.get("compression_metrics") or {}).get("cases", [])
            if isinstance(r.get("semantic_pointer"), dict)
            and (r["semantic_pointer"].get("graph_wire_influence_v1"))
        )
        return {
            "combo_id": "atom05_full_wire_selective",
            "metrics": _metrics(report),
            "semantic_pointer_with_wire_count": sp_n,
        }

    combos = [
        _eval_combo(src, "atom05_full_baseline", BASE_MUST_KEEP, bridge=False),
        _eval_wire_selective(),
        _eval_combo(
            src,
            "atom05_full_ssot_allowlist",
            BASE_MUST_KEEP,
            bridge=True,
            allowlist=frozenset({"ssot"}),
        ),
    ]

    b0 = combos[0]["metrics"]
    w1 = combos[1]["metrics"]
    doc = {
        "schema": "comp_atom05_full_v2_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "b_track_comp_atom05",
        "active_report_untouched": True,
        "gate_status": status,
        "cases_total": len(cases),
        "bridge_boost_case_count": boost_n,
        "combos": combos,
        "deltas_wire_selective_vs_full_baseline": {
            k: round(w1[k] - b0[k], 6)
            for k in ("global_token_saving_rate", "avg_reconstruction_fidelity_jaccard")
            if isinstance(b0.get(k), (int, float))
        },
        "compare_subset": "reports/constitution/btrack_pilot/comp_atom05_graph_wire_bridge_sweep_v1.json",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT.relative_to(ROOT)),
                "deltas": doc["deltas_wire_selective_vs_full_baseline"],
                "combos": {c["combo_id"]: c["metrics"] for c in combos},
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
