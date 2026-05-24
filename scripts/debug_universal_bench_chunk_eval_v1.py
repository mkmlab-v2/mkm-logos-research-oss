#!/usr/bin/env python3
"""Debug one IJEOMA chunk case economy eval (B-track diagnostic JSON only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHUNK_LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_chunk_eval_debug_v1.json"


def main() -> int:
    from scripts.comp_graphrag_philosophy_compression_sweep_v1 import BASE_MUST_KEEP, _base_eval_kwargs
    from scripts.compression_profile_v1 import profile_evaluate_report_kwargs
    from scripts.report_multilens_performance_eval import evaluate_report

    doc = json.loads(CHUNK_LANE.read_text(encoding="utf-8"))
    cases = doc.get("compression_cases") or []
    if not cases:
        print(json.dumps({"error": "no_cases"}, ensure_ascii=False))
        return 1

    case = cases[0]
    src = {"schema": "multilens_performance_eval_input_v1", "compression_cases": [case]}
    kw = _base_eval_kwargs()
    kw.update(profile_evaluate_report_kwargs("economy"))
    report = evaluate_report(src, must_keep=set(BASE_MUST_KEEP), graph_wire_selective_bridge=False, **kw)
    cm = (report.get("compression_metrics") or {}).get("cases") or []
    row = cm[0] if cm else {}

    diag = {
        "schema": "comp_universal_bench_chunk_eval_debug_v1",
        "research_only": True,
        "case_id": case.get("id"),
        "raw_text_len": len(str(case.get("raw_text") or "")),
        "raw_text_preview": str(case.get("raw_text") or "")[:120],
        "global_metrics": report.get("compression_metrics", {}).get("global"),
        "case_metrics": row,
        "eval_contract": doc.get("eval_contract"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(diag, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "diag": diag}, ensure_ascii=False)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
