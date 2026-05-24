#!/usr/bin/env python3
"""Per-case Jaccard delta: economy baseline vs economy+wire for bridge_boost cases only."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BOOST = ROOT / "reports/constitution/btrack_pilot/comp_atom05_bridge_boost_detail_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_atom05_bridge_boost_per_case_delta_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eval_case_jaccard(case: dict, *, wire_inf: dict | None) -> float | None:
    from scripts.report_multilens_performance_eval import evaluate_report  # noqa: WPS433
    from scripts.comp_graphrag_philosophy_compression_sweep_v1 import (  # noqa: WPS433
        BASE_MUST_KEEP,
        _base_eval_kwargs,
    )

    cid = str(case.get("case_id") or case.get("id") or "")
    mini = {
        "schema": "multilens_performance_eval_report",
        "compression_cases": [case],
    }
    inf_map = {cid: wire_inf} if wire_inf and cid else None
    rep = evaluate_report(
        mini,
        must_keep=set(BASE_MUST_KEEP),
        apply_gematria_4d_bridge_policy=False,
        graph_wire_selective_bridge=bool(wire_inf),
        case_graph_wire_influence=inf_map,
        emit_semantic_pointer=bool(wire_inf),
        **_base_eval_kwargs(),
    )
    cases = (rep.get("compression_metrics") or {}).get("cases") or []
    if not cases:
        return None
    return float((cases[0] or {}).get("reconstruction_fidelity_jaccard") or 0)


def main() -> int:
    from scripts.mkm_graph_wire_bridge_influence_v1 import (  # noqa: WPS433
        build_influence_map_from_compression_cases,
        wire_atom_ids_from_poc,
    )

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    cases = list(src.get("compression_cases") or [])
    influence = build_influence_map_from_compression_cases(
        cases, wire_atom_ids=wire_atom_ids_from_poc()
    )
    boost_doc = json.loads(BOOST.read_text(encoding="utf-8")) if BOOST.is_file() else {}
    boost_ids = {
        str(r.get("case_id"))
        for r in (boost_doc.get("bridge_boost_cases") or [])
        if r.get("case_id")
    }

    rows: list[dict[str, Any]] = []
    for case in cases:
        cid = str(case.get("id") or case.get("case_id") or "")
        if cid not in boost_ids:
            continue
        inf = influence.get(cid)
        eval_case = dict(case)
        eval_case.setdefault("case_id", cid)
        j0 = _eval_case_jaccard(eval_case, wire_inf=None)
        j1 = _eval_case_jaccard(eval_case, wire_inf=inf)
        rows.append(
            {
                "case_id": cid,
                "jaccard_baseline": j0,
                "jaccard_wire": j1,
                "jaccard_delta_pp": (j1 - j0) if j0 is not None and j1 is not None else None,
                "wire_influence_score": (inf or {}).get("wire_influence_score"),
            }
        )

    report = {
        "schema": "comp_atom05_bridge_boost_per_case_delta_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "boost_case_count": len(rows),
        "rows": rows,
        "mean_delta_pp": (
            sum(r["jaccard_delta_pp"] for r in rows if r.get("jaccard_delta_pp") is not None)
            / max(1, sum(1 for r in rows if r.get("jaccard_delta_pp") is not None))
        ),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "cases": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
